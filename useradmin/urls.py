from django.urls import path
from useradmin import views

app_name = "useradmin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("products/", views.products, name="dashboard-products"),
    path("add-products/", views.add_product, name="dashboard-add-products"),
    path("edit-products/<pid>/", views.edit_product, name="dashboard-edit-products"),
    path("delete-products/<pid>/", views.delete_product, name="dashboard-delete-products"),
    path("orders/", views.orders, name="orders"),
    # <int:id>, not <id>: a non-numeric id used to reach the ORM and raise
    # ValueError (a 500) instead of simply not matching the route.
    path("order_detail/<int:id>/", views.order_detail, name="order_detail"),
    path("change_order_status/<oid>/", views.change_order_status, name="change_order_status"),
    path("verify_khqr_payment/<oid>/", views.verify_khqr_payment, name="verify_khqr_payment"),
    path("confirm_cod_payment/<oid>/", views.confirm_cod_payment, name="confirm_cod_payment"),
    path("shop_page/", views.shop_page, name="shop_page"),
    path("reviews/", views.reviews, name="reviews"),
    path("settings/", views.settings, name="settings"),
    path("change_password/", views.change_password, name="change_password"),
]
