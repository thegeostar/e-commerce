from django.urls import path
from core.views import save_checkout_info, add_to_cart, add_to_wishlist, ajax_add_review, ajax_contact_form, cart_view, cash_on_delivery_view, category_list_view, category_product_list__view, checkout, customer_dashboard, delete_item_from_cart, filter_product, index, khqr_payment_view, khqr_submitted_view, make_address_default, order_detail, payment_completed_view, product_detail_view, product_list_view, remove_wishlist, search_view, tag_list, update_cart, vendor_detail_view, vendor_list_view, wishlist_view, contact, about_us, purchase_guide, privacy_policy, terms_of_service

app_name = "core"

urlpatterns = [

    # Homepage
    path("", index, name="index"),
    path("products/", product_list_view, name="product-list"),
    path("product/<pid>/", product_detail_view, name="product-detail"),
    path("category/", category_list_view, name="category-list"),
    path("category/<cid>/", category_product_list__view, name="category-product-list"),
    path("vendors/", vendor_list_view, name="vendor-list"),
    path("vendor/<vid>/", vendor_detail_view, name="vendor-detail"),
    path("products/tag/<slug:tag_slug>/", tag_list, name="tags"),
    path("ajax-add-review/<int:pid>/", ajax_add_review, name="ajax-add-review"),
    path("search/", search_view, name="search"),
    path("filter-products/", filter_product, name="filter-product"),
    path("add-to-cart/", add_to_cart, name="add-to-cart"),
    path("cart/", cart_view, name="cart"),
    path("delete-from-cart/", delete_item_from_cart, name="delete-from-cart"),
    path("update-cart/", update_cart, name="update-cart"),
    path("save_checkout_info/", save_checkout_info, name="save_checkout_info"),
    path("checkout/<oid>/", checkout, name="checkout"),
    path("khqr/<oid>/", khqr_payment_view, name="khqr-payment"),
    path("khqr/<oid>/submitted/", khqr_submitted_view, name="khqr-submitted"),
    path("cash-on-delivery/<oid>/", cash_on_delivery_view, name="cash-on-delivery"),
    path("payment-completed/<oid>/", payment_completed_view, name="payment-completed"),
    path("dashboard/", customer_dashboard, name="dashboard"),
    path("dashboard/order/<int:id>", order_detail, name="order-detail"),
    path("make-default-address/", make_address_default, name="make-default-address"),
    path("wishlist/", wishlist_view, name="wishlist"),
    path("add-to-wishlist/", add_to_wishlist, name="add-to-wishlist"),
    path("remove-from-wishlist/", remove_wishlist, name="remove-from-wishlist"),
    path("contact/", contact, name="contact"),
    path("ajax-contact-form/", ajax_contact_form, name="ajax-contact-form"),
    path("about_us/", about_us, name="about_us"),
    path("purchase_guide/", purchase_guide, name="purchase_guide"),
    path("privacy_policy/", privacy_policy, name="privacy_policy"),
    path("terms_of_service/", terms_of_service, name="terms_of_service"),
]