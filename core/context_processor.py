from core.models import Product, Category, Vendor, wishlist_model, Address
from django.db.models import Min, Max


def default(request):
    categories = Category.objects.all()
    vendors = Vendor.objects.all()

    min_max_price = Product.objects.aggregate(Min("price"), Max("price"))

    if request.user.is_authenticated:
        wishlist = wishlist_model.objects.filter(user=request.user)
        address = (
            Address.objects.filter(user=request.user, status=True).first()
            or Address.objects.filter(user=request.user).last()
        )
    else:
        wishlist = wishlist_model.objects.none()
        address = None

    # Mini cart for the header dropdown. Guarded because a malformed session
    # entry here would otherwise raise on every single page of the site.
    cart_data = request.session.get('cart_data_obj') or {}
    mini_cart_total = 0
    for item in cart_data.values():
        try:
            mini_cart_total += int(item['qty']) * float(item['price'])
        except (KeyError, TypeError, ValueError):
            continue

    return {
        'categories': categories,
        'wishlist': wishlist,
        'address': address,
        'vendors': vendors,
        'min_max_price': min_max_price,
        'mini_cart': cart_data,
        'mini_cart_total': mini_cart_total,
    }
