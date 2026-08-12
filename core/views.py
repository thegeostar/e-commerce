from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from taggit.models import Tag
from core.models import RATING, Coupon, Product, Category, Vendor, CartOrder, CartOrderProducts, ProductReview, wishlist_model, Address
from userauths.models import ContactUs, Profile
from core.forms import KHQRPaymentForm, ProductReviewForm
from django.template.loader import render_to_string
from django.contrib import messages

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.staticfiles import finders
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

import calendar
from decimal import Decimal, InvalidOperation
from django.db.models import Count, Avg, F, Sum
from django.db.models.functions import ExtractMonth


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Nobody can be stopped from typing ?id=abc into the address bar, and handing
# that straight to the ORM raises ValueError — a 500 error page for what is
# really just a bad request. Every value that arrives from a query string or a
# form goes through one of these first.

def _int_or_none(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _int_list(raw_values):
    """Coerce a list of query-string values to ints, dropping the junk."""
    return [n for n in (_int_or_none(v) for v in raw_values) if n is not None]


def _decimal_or_none(raw):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value.is_finite() else None


# The star ratings the model actually offers, as a set for cheap membership.
VALID_RATINGS = {value for value, _ in RATING}

# Every listing page ("Sort by" dropdown) understands the same values.
SORT_OPTIONS = {
    "featured": ("Featured", ["-featured", "-id"]),
    "price": ("Price: Low to High", ["price"]),
    "-price": ("Price: High to Low", ["-price"]),
    "newest": ("Newest", ["-date"]),
    "discount": ("Biggest discount", ["-discount_amount"]),
    "rating": ("Avg. Rating", ["-average_rating"]),
}


def sort_products(request, products):
    """Apply ?sort= to a product queryset.

    Returns (queryset, key, label) so the template can highlight the option
    that is currently active. Unknown values fall back to "featured" instead
    of raising, because the value comes straight off the query string.
    """
    key = request.GET.get("sort", "featured")
    if key not in SORT_OPTIONS:
        key = "featured"

    label, ordering = SORT_OPTIONS[key]

    if key == "discount":
        products = products.annotate(discount_amount=F("old_price") - F("price"))
    elif key == "rating":
        products = products.annotate(average_rating=Avg("reviews__rating"))

    return products.order_by(*ordering), key, label


def published_products():
    return Product.objects.filter(product_status="published").select_related("category", "vendor")


def get_deals_context(limit=4):
    """The biggest live discounts, plus the deadline the countdown ticks to.

    A "deal" is simply a published product priced below its old price. If
    nothing is discounted the homepage section hides itself rather than
    showing invented products.
    """
    deals = (
        published_products()
        .filter(old_price__gt=F("price"))
        .annotate(discount_amount=F("old_price") - F("price"))
        .order_by("-discount_amount")[:limit]
    )

    end_of_day = timezone.localtime().replace(hour=23, minute=59, second=59, microsecond=0)

    return {
        "deals": deals,
        "deal_ends": end_of_day.strftime("%Y/%m/%d %H:%M:%S"),
    }


def _products_by_title(titles):
    """Map order-line titles back to products, keeping the given order.

    CartOrderProducts stores the item name as text rather than a foreign key,
    so "top selling" has to be matched by title. Anything that has since been
    renamed or deleted simply drops out of the list.
    """
    by_title = {p.title: p for p in published_products().filter(title__in=titles)}
    return [by_title[t] for t in titles if t in by_title]


def _top_selling(limit=3):
    sold = (
        CartOrderProducts.objects.filter(order__paid_status=True)
        .values("item")
        .annotate(units=Sum("qty"))
        .order_by("-units")[: limit * 3]
    )
    products = _products_by_title([row["item"] for row in sold])[:limit]

    # A brand new shop has no paid orders yet; show the newest stock instead
    # of an empty column.
    if not products:
        products = list(published_products().order_by("-date")[:limit])
    return products


# ---------------------------------------------------------------------------
# Storefront
# ---------------------------------------------------------------------------

def index(request):
    # Fetched once and split up in Python — one query instead of one per tab.
    products = list(published_products().order_by("-featured", "-id"))

    # "Popular Products" tabs. The tabs used to be hardcoded to the demo
    # shop's categories (Milks & Dairies, Coffes & Teas, ...) with static
    # markup behind them, so every tab but the first showed products that do
    # not exist here. They are now built from the real categories.
    category_tabs = []
    for category in Category.objects.all():
        tab_products = [p for p in products if p.category_id == category.id]
        if tab_products:
            category_tabs.append({"category": category, "products": tab_products[:10]})

    context = {
        "products": products[:10],
        "category_tabs": category_tabs,
        "top_selling": _top_selling(),
        "trending": published_products().annotate(review_count=Count("reviews")).order_by("-review_count", "-id")[:3],
        "recently_added": published_products().order_by("-date")[:3],
        "top_rated": published_products().annotate(average_rating=Avg("reviews__rating")).order_by(F("average_rating").desc(nulls_last=True), "-id")[:3],
    }
    context.update(get_deals_context())

    return render(request, 'core/index.html', context)


def product_list_view(request):
    products, sort, sort_label = sort_products(request, published_products())
    tags = Tag.objects.all().order_by("-id")[:6]

    context = {
        "products": products,
        "tags": tags,
        "sort": sort,
        "sort_label": sort_label,
    }
    context.update(get_deals_context())

    return render(request, 'core/product-list.html', context)


def category_list_view(request):
    categories = Category.objects.all()

    context = {
        "categories": categories
    }
    return render(request, 'core/category-list.html', context)


def category_product_list__view(request, cid):
    category = get_object_or_404(Category, cid=cid)
    products, sort, sort_label = sort_products(request, published_products().filter(category=category))

    context = {
        "category": category,
        "products": products,
        "sort": sort,
        "sort_label": sort_label,
    }
    return render(request, "core/category-product-list.html", context)


def vendor_list_view(request):
    query = request.GET.get("q", "").strip()

    vendor_list = Vendor.objects.all()
    if query:
        vendor_list = vendor_list.filter(title__icontains=query)

    context = {
        # Not "vendors": the context processor already puts every vendor under
        # that name for the shop filters, and shadowing it here would break the
        # sidebar on this page.
        "vendor_list": vendor_list,
        "query": query,
    }
    return render(request, "core/vendor-list.html", context)


def vendor_detail_view(request, vid):
    vendor = get_object_or_404(Vendor, vid=vid)
    products, sort, sort_label = sort_products(request, published_products().filter(vendor=vendor))

    context = {
        "vendor": vendor,
        "products": products,
        "sort": sort,
        "sort_label": sort_label,
    }
    return render(request, "core/vendor-detail.html", context)


def product_detail_view(request, pid):
    product = get_object_or_404(Product, pid=pid)
    products = published_products().filter(category=product.category).exclude(pid=pid)[:4]

    reviews = ProductReview.objects.filter(product=product).order_by("-date")
    average_rating = ProductReview.objects.filter(product=product).aggregate(rating=Avg('rating'))
    review_form = ProductReviewForm()

    make_review = True
    address = None

    if request.user.is_authenticated:
        address = Address.objects.filter(status=True, user=request.user).first()
        user_review_count = ProductReview.objects.filter(user=request.user, product=product).count()

        if user_review_count > 0:
            make_review = False

    p_image = product.p_images.all()

    context = {
        "p": product,
        "address": address,
        "make_review": make_review,
        "review_form": review_form,
        "p_image": p_image,
        "average_rating": average_rating,
        "reviews": reviews,
        "products": products,
        "new_products": published_products().exclude(pid=pid).order_by("-date")[:3],
    }

    return render(request, "core/product-detail.html", context)


def tag_list(request, tag_slug=None):
    products = published_products()

    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        products = products.filter(tags__in=[tag])

    products, sort, sort_label = sort_products(request, products)

    context = {
        "products": products,
        "tag": tag,
        "sort": sort,
        "sort_label": sort_label,
    }

    return render(request, "core/tag.html", context)


@login_required
@require_POST
def ajax_add_review(request, pid):
    product = get_object_or_404(Product, pk=pid)
    user = request.user

    review_text = request.POST.get("review", "").strip()
    rating = _int_or_none(request.POST.get("rating"))
    if not review_text or rating is None:
        return JsonResponse({"bool": False, "error": "Review and rating are required."}, status=400)

    # `choices` is not enforced by the database, so a hand-crafted POST could
    # otherwise store a 99-star review and skew every average on the site.
    if rating not in VALID_RATINGS:
        return JsonResponse(
            {"bool": False, "error": "Rating must be between 1 and 5."}, status=400)

    # product_detail_view already hides the form from anyone who has reviewed
    # this product, but that is only the template. Without the same check here
    # a direct POST could add unlimited reviews and move the average at will.
    if ProductReview.objects.filter(user=user, product=product).exists():
        return JsonResponse(
            {"bool": False, "error": "You have already reviewed this product."},
            status=400)

    ProductReview.objects.create(
        user=user,
        product=product,
        review=review_text,
        rating=rating,
    )

    context = {
        'user': user.username,
        'review': review_text,
        'rating': rating,
    }

    average_reviews = ProductReview.objects.filter(product=product).aggregate(rating=Avg("rating"))

    return JsonResponse({
        'bool': True,
        'context': context,
        'average_reviews': average_reviews
    })


def search_view(request):
    query = request.GET.get("q", "").strip()
    cid = request.GET.get("category", "").strip()

    category = Category.objects.filter(cid=cid).first() if cid else None

    if query or category:
        products = published_products()
        if query:
            products = products.filter(title__icontains=query)
        if category:
            products = products.filter(category=category)
    else:
        products = Product.objects.none()

    products, sort, sort_label = sort_products(request, products)

    context = {
        "products": products,
        "query": query,
        "search_category": category,
        "sort": sort,
        "sort_label": sort_label,
    }
    return render(request, "core/search.html", context)


def filter_product(request):
    categories = request.GET.getlist("category[]")
    vendors = request.GET.getlist("vendor[]")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    products = Product.objects.filter(product_status="published").order_by("-id").distinct()

    min_price = _decimal_or_none(min_price)
    max_price = _decimal_or_none(max_price)
    categories = _int_list(categories)
    vendors = _int_list(vendors)

    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)
    if categories:
        products = products.filter(category__id__in=categories).distinct()
    if vendors:
        products = products.filter(vendor__id__in=vendors).distinct()

    data = render_to_string("core/async/product-list.html", {"products": products})
    return JsonResponse({"data": data})


# One order should not be able to claim the whole warehouse, and an
# astronomical quantity overflows the order total further down the line.
MAX_CART_QTY = 999


def _clean_qty(raw, default=1):
    qty = _int_or_none(raw)
    if qty is None or qty < 1:
        return default
    return min(qty, MAX_CART_QTY)


def add_to_cart(request):
    product_id = _int_or_none(request.GET.get("id"))
    if product_id is None:
        return HttpResponseBadRequest("Missing product id")

    product = Product.objects.filter(id=product_id).first()
    if product is None:
        return HttpResponseBadRequest("Unknown product")

    cart_data = request.session.get('cart_data_obj', {})
    key = str(product.id)

    # Pressing "Add" again tops the line up instead of replacing it. The
    # listing cards always send qty=1, so replacing meant a second click did
    # nothing at all; on the product page it silently discarded the first
    # quantity. Setting an exact number is what the cart's own qty box is for.
    requested = _clean_qty(request.GET.get("qty"))
    already_in_cart = _int_or_none((cart_data.get(key) or {}).get("qty")) or 0
    qty = min(already_in_cart + requested, MAX_CART_QTY)

    # Title, price and image are re-read from the database every time, so a
    # line added before a price change does not keep the stale price.
    cart_data[key] = {
        'title': product.title,
        'qty': qty,
        'price': str(product.price),
        'image': product.image.url if product.image else "",
        'pid': product.pid,
    }
    request.session['cart_data_obj'] = cart_data

    return JsonResponse({"data": cart_data, 'totalcartitems': len(cart_data)})


def cart_view(request):
    cart_data = request.session.get('cart_data_obj', {})

    # An empty cart renders its own empty state rather than bouncing the user
    # back to the homepage, which looked like the Cart link was broken.
    cart_total_amount = 0
    for p_id, item in cart_data.items():
        cart_total_amount += int(item['qty']) * float(item['price'])

    return render(request, "core/cart.html", {
        "cart_data": cart_data,
        'totalcartitems': len(cart_data),
        'cart_total_amount': cart_total_amount,
    })


def _render_cart(cart_data):
    cart_total_amount = 0
    for p_id, item in cart_data.items():
        cart_total_amount += int(item['qty']) * float(item['price'])

    context = render_to_string("core/async/cart-list.html", {
        "cart_data": cart_data,
        'totalcartitems': len(cart_data),
        'cart_total_amount': cart_total_amount,
    })
    return JsonResponse({"data": context, 'totalcartitems': len(cart_data)})


def delete_item_from_cart(request):
    product_id = str(request.GET.get("id", ""))

    cart_data = request.session.get('cart_data_obj', {})
    if product_id in cart_data:
        del cart_data[product_id]
        request.session['cart_data_obj'] = cart_data

    return _render_cart(cart_data)


def update_cart(request):
    product_id = str(request.GET.get("id", ""))

    cart_data = request.session.get('cart_data_obj', {})
    if product_id in cart_data:
        cart_data[product_id]['qty'] = _clean_qty(request.GET.get("qty"))
        request.session['cart_data_obj'] = cart_data

    return _render_cart(cart_data)


def _pending_order(user):
    """The checkout the customer has open but has not paid for yet.

    An order becomes "committed" the moment a payment method is chosen, so
    anything still without one is a draft from a checkout that was never
    carried through — safe to reuse rather than pile up beside a new one.
    """
    return (
        CartOrder.objects
        .filter(user=user, paid_status=False, payment_method__isnull=True)
        .order_by("-id")
        .first()
    )


@login_required
@require_POST
@transaction.atomic
def save_checkout_info(request):
    """Turn the session cart into an order, then hand off to the payment page.

    Re-entering checkout reuses the customer's pending order instead of
    creating another one. Submitting the form twice — a double click, or the
    back button followed by "Proceed to checkout" — used to leave a duplicate
    order behind on every attempt.
    """
    cart_data = request.session.get('cart_data_obj', {})
    if not cart_data:
        messages.warning(request, "Your cart is empty")
        return redirect("core:index")

    total_amount = 0
    for p_id, item in cart_data.items():
        total_amount += int(item['qty']) * float(item['price'])

    details = {
        "price": total_amount,
        "full_name": request.POST.get("full_name"),
        "email": request.POST.get("email"),
        "phone": request.POST.get("mobile"),
        "address": request.POST.get("address"),
        "city": request.POST.get("city"),
        "state": request.POST.get("state"),
        "country": request.POST.get("country"),
    }

    order = _pending_order(request.user)
    if order is None:
        order = CartOrder.objects.create(user=request.user, **details)
    else:
        for field, value in details.items():
            setattr(order, field, value)
        # `price` has just been recalculated from the cart, so any discount
        # from a previous visit is gone. Releasing the coupons lets the
        # customer apply one again instead of being told it is already active
        # while paying the undiscounted total.
        order.saved = 0
        order.coupons.clear()
        order.save()
        order.cartorderproducts_set.all().delete()

    for p_id, item in cart_data.items():
        CartOrderProducts.objects.create(
            order=order,
            invoice_no="INVOICE_NO-" + str(order.id),
            item=item['title'],
            image=item['image'],
            qty=item['qty'],
            price=item['price'],
            total=float(item['qty']) * float(item['price'])
        )

    return redirect("core:checkout", order.oid)


@login_required
def checkout(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)
    order_items = CartOrderProducts.objects.filter(order=order)

    if request.method == "POST":
        code = request.POST.get("code")
        coupon = Coupon.objects.filter(code=code, active=True).first()
        if coupon:
            if coupon in order.coupons.all():
                messages.warning(request, "Coupon already activated")
                return redirect("core:checkout", order.oid)
            else:
                discount = order.price * coupon.discount / 100

                order.coupons.add(coupon)
                order.price -= discount
                order.saved += discount
                order.save()

                messages.success(request, "Coupon Activated")
                return redirect("core:checkout", order.oid)
        else:
            messages.error(request, "Coupon Does Not Exists")

    context = {
        "order": order,
        "order_items": order_items,
    }
    return render(request, "core/checkout.html", context)


@login_required
@require_POST
def cash_on_delivery_view(request, oid):
    """Place the order to be paid in cash when the courier hands it over.

    Nothing is collected online, so the order stays unpaid until the seller
    marks it paid from the dashboard after the courier returns with the money.
    """
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)

    if order.paid_status:
        return redirect("core:payment-completed", order.oid)

    order.payment_method = "cod"
    order.save()

    # The cart has become an order; leaving it filled would let the buyer
    # place the same order twice by going back.
    request.session['cart_data_obj'] = {}

    messages.success(request, "Order placed. Please have the cash ready when your delivery arrives.")
    return redirect("core:payment-completed", order.oid)


@login_required
def payment_completed_view(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)

    context = {
        "order": order,
        "order_items": CartOrderProducts.objects.filter(order=order),
    }
    return render(request, 'core/payment-completed.html', context)


@login_required
def khqr_payment_view(request, oid):
    """
    The same static KHQR is shown for every order, so the bank gives us no way
    to tell which transfer belongs to which order. The buyer therefore submits
    their transaction ID and the shop owner approves it from the seller
    dashboard. Nothing here ever sets `paid_status` — only approval does.
    """
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)

    if order.paid_status:
        return redirect("core:payment-completed", order.oid)

    if request.method == "POST":
        form = KHQRPaymentForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            order.payment_method = "khqr"
            order.khqr_status = "pending"
            order.khqr_submitted_at = timezone.now()
            order.save()

            request.session['cart_data_obj'] = {}

            messages.success(request, "Payment submitted. We will confirm your order shortly.")
            return redirect("core:khqr-submitted", order.oid)
        messages.error(request, "Please enter your transaction ID.")
    else:
        form = KHQRPaymentForm(instance=order)

    context = {
        "order": order,
        "order_items": CartOrderProducts.objects.filter(order=order),
        "form": form,
        "khqr_merchant_name": settings.KHQR_MERCHANT_NAME,
        "khqr_bank_name": settings.KHQR_BANK_NAME,
        "khqr_image": settings.KHQR_IMAGE,
        "khqr_image_found": bool(finders.find(settings.KHQR_IMAGE)),
        "khqr_pay_link": settings.KHQR_PAY_LINK,
    }
    return render(request, "core/khqr-payment.html", context)


@login_required
def khqr_submitted_view(request, oid):
    order = get_object_or_404(CartOrder, oid=oid, user=request.user)

    context = {
        "order": order,
        "khqr_bank_name": settings.KHQR_BANK_NAME,
    }
    return render(request, "core/khqr-submitted.html", context)


@login_required
def customer_dashboard(request):
    orders_list = CartOrder.objects.filter(user=request.user).order_by("-id")
    address = Address.objects.filter(user=request.user)

    orders = CartOrder.objects.filter(user=request.user).annotate(month=ExtractMonth("order_date")).values("month").annotate(count=Count("id")).values("month", "count")
    month = []
    total_orders = []

    for i in orders:
        if i["month"]:
            month.append(calendar.month_name[i["month"]])
            total_orders.append(i["count"])

    if request.method == "POST":
        Address.objects.create(
            user=request.user,
            address=request.POST.get("address"),
            mobile=request.POST.get("mobile"),
        )
        messages.success(request, "Address Added Successfully.")
        return redirect("core:dashboard")

    user_profile, _ = Profile.objects.get_or_create(user=request.user)

    context = {
        "user_profile": user_profile,
        "orders": orders,
        "orders_list": orders_list,
        "address": address,
        "month": month,
        "total_orders": total_orders,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def order_detail(request, id):
    order = get_object_or_404(CartOrder, user=request.user, id=id)
    order_items = CartOrderProducts.objects.filter(order=order)

    context = {
        "order_items": order_items,
    }
    return render(request, 'core/order-detail.html', context)


@login_required
def make_address_default(request):
    """Promote one saved address to the default.

    The target is confirmed to exist *before* the old default is cleared —
    clearing first meant a bad id left the customer with no default at all.
    """
    address = Address.objects.filter(
        id=_int_or_none(request.GET.get("id")), user=request.user).first()
    if address is None:
        return JsonResponse({"boolean": False}, status=404)

    Address.objects.filter(user=request.user).update(status=False)
    Address.objects.filter(pk=address.pk).update(status=True)

    return JsonResponse({"boolean": True})


def _user_wishlist(user):
    return wishlist_model.objects.filter(user=user).select_related("product")


@login_required
def wishlist_view(request):
    context = {
        "wishlist_items": _user_wishlist(request.user),
    }
    return render(request, "core/wishlist.html", context)


@login_required
def add_to_wishlist(request):
    product_id = _int_or_none(request.GET.get("id"))
    if product_id is None:
        return JsonResponse({"bool": False, "error": "Unknown product"}, status=400)

    product = get_object_or_404(Product, id=product_id)

    wishlist_model.objects.get_or_create(user=request.user, product=product)

    return JsonResponse({"bool": True, "count": _user_wishlist(request.user).count()})


@login_required
def remove_wishlist(request):
    wishlist_model.objects.filter(
        id=_int_or_none(request.GET.get("id")), user=request.user).delete()

    wishlist_items = _user_wishlist(request.user)
    table = render_to_string('core/partials/wishlist-table.html', {"wishlist_items": wishlist_items}, request=request)

    return JsonResponse({'data': table, 'count': wishlist_items.count()})


def contact(request):
    return render(request, "core/contact.html")


def ajax_contact_form(request):
    full_name = request.GET.get("full_name", "").strip()
    email = request.GET.get("email", "").strip()
    phone = request.GET.get("phone", "").strip()
    subject = request.GET.get("subject", "").strip()
    message = request.GET.get("message", "").strip()

    if not all([full_name, email, subject, message]):
        return JsonResponse(
            {"data": {"bool": False, "message": "Please fill in every field."}},
            status=400,
        )

    ContactUs.objects.create(
        full_name=full_name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )

    data = {
        "bool": True,
        "message": "Message Sent Successfully"
    }

    return JsonResponse({"data": data})


def about_us(request):
    return render(request, "core/about_us.html")


def _trending_sidebar():
    """Products for the "Trending Now" widget on the static content pages."""
    return {"trending": published_products().annotate(review_count=Count("reviews")).order_by("-review_count", "-id")[:4]}


def purchase_guide(request):
    return render(request, "core/purchase_guide.html", _trending_sidebar())


def privacy_policy(request):
    return render(request, "core/privacy_policy.html", _trending_sidebar())


def terms_of_service(request):
    return render(request, "core/terms_of_service.html", _trending_sidebar())
