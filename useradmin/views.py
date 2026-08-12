from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password


from core.models import CartOrder, CartOrderProducts, Product, Category, ProductReview, STATUS_CHOICE
from userauths.models import Profile, User
from useradmin.forms import AddProductForm
from useradmin.decorators import admin_required

import datetime



@admin_required
def dashboard(request):
    revenue = CartOrder.objects.aggregate(price=Sum("price"))
    total_orders_count = CartOrder.objects.all()
    all_products = Product.objects.all()
    all_categories = Category.objects.all()
    new_customers = User.objects.all().order_by("-id")[:6]
    latest_orders = CartOrder.objects.all()

    this_month = datetime.datetime.now().month
    monthly_revenue = CartOrder.objects.filter(order_date__month=this_month).aggregate(price=Sum("price"))

    
    context = {
        "monthly_revenue": monthly_revenue,
        "revenue": revenue,
        "all_products": all_products,
        "all_categories": all_categories,
        "new_customers": new_customers,
        "latest_orders": latest_orders,
        "total_orders_count": total_orders_count,
    }
    return render(request, "useradmin/dashboard.html", context)

@admin_required
def products(request):
    all_products = Product.objects.all()
    all_categories = Category.objects.all()
    
    context = {
        "all_products": all_products,
        "all_categories": all_categories,
    }
    return render(request, "useradmin/products.html", context)

@admin_required
def add_product(request):
    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.save()
            form.save_m2m()
            return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm()
    context = {
        'form':form
    }
    return render(request, "useradmin/add-products.html", context)

@admin_required
def edit_product(request, pid):
    product = get_object_or_404(Product, pid=pid)

    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.save()
            form.save_m2m()
            return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm(instance=product)
    context = {
        'form':form,
        'product':product,
    }
    return render(request, "useradmin/edit-products.html", context)

@admin_required
@require_POST
def delete_product(request, pid):
    product = get_object_or_404(Product, pid=pid)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect("useradmin:dashboard-products")

@admin_required
def orders(request):
    orders = CartOrder.objects.all()
    context = {
        'orders':orders,
    }
    return render(request, "useradmin/orders.html", context)

@admin_required
def order_detail(request, id):
    order = get_object_or_404(CartOrder, id=id)
    order_items = CartOrderProducts.objects.filter(order=order)
    context = {
        'order':order,
        'order_items':order_items
    }
    return render(request, "useradmin/order_detail.html", context)

@admin_required
@require_POST
def change_order_status(request, oid):
    order = get_object_or_404(CartOrder, oid=oid)
    status = request.POST.get("status")

    valid_statuses = [choice[0] for choice in STATUS_CHOICE]
    if status in valid_statuses:
        order.product_status = status
        order.save()
        messages.success(request, f"Order status changed to {status}")
    else:
        messages.error(request, "Please choose a valid order status.")

    return redirect("useradmin:order_detail", order.id)

@admin_required
@require_POST
def verify_khqr_payment(request, oid):
    """
    KHQR transfers land in the bank account with no order reference, so the
    shop owner checks the buyer's transaction ID against the bank statement
    and approves it here. This is the only place a KHQR order becomes paid.
    """
    order = get_object_or_404(CartOrder, oid=oid)
    action = request.POST.get("action")

    if action == "approve":
        order.khqr_status = "approved"
        order.paid_status = True
        order.save()
        messages.success(request, f"KHQR payment approved. Order #{order.oid} is now marked as paid.")
    elif action == "reject":
        order.khqr_status = "rejected"
        order.paid_status = False
        order.save()
        messages.warning(request, f"KHQR payment rejected. The buyer can submit a new transaction ID.")
    else:
        messages.error(request, "Please choose approve or reject.")

    return redirect("useradmin:order_detail", order.id)

@admin_required
@require_POST
def confirm_cod_payment(request, oid):
    """Mark a cash-on-delivery order paid once the courier hands over the money."""
    order = get_object_or_404(CartOrder, oid=oid)

    if order.payment_method != "cod":
        messages.error(request, "This order was not placed as cash on delivery.")
    else:
        order.paid_status = True
        order.save()
        messages.success(request, f"Cash collected. Order #{order.oid} is now marked as paid.")

    return redirect("useradmin:order_detail", order.id)

@admin_required
def shop_page(request):
    products = Product.objects.filter(user=request.user)
    revenue = CartOrder.objects.filter(paid_status=True).aggregate(price=Sum("price"))
    total_sales = CartOrderProducts.objects.filter(order__paid_status=True).aggregate(qty=Sum("qty"))

    context = {
        'products':products,
        'revenue':revenue,
        'total_sales':total_sales,
    }
    return render(request, "useradmin/shop_page.html", context)

@admin_required
def reviews(request):
    reviews = ProductReview.objects.all()
    context = {
        'reviews':reviews,
    }
    return render(request, "useradmin/reviews.html", context)

@admin_required
def settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        bio = request.POST.get("bio")
        address = request.POST.get("address")
        country = request.POST.get("country")

        if image != None:
            profile.image = image
        profile.full_name = full_name
        profile.phone = phone
        profile.bio = bio
        profile.address = address
        profile.country = country

        profile.save()
        messages.success(request, "Profile Updated Successfully")
        return redirect("useradmin:settings")
    
    context = {
        'profile':profile,
    }
    return render(request, "useradmin/settings.html", context)

@admin_required
def change_password(request):
    user = request.user

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Confirm Password and New Password Does Not Match")
            return redirect("useradmin:change_password")
        
        if check_password(old_password, user.password):
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password Changed Successfully")
            return redirect("useradmin:change_password")
        else:
            messages.error(request, "Old password is not correct")
            return redirect("useradmin:change_password")
    
    return render(request, "useradmin/change_password.html")
