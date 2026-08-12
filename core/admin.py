from django.contrib import admin
from core.models import CartOrderProducts, Coupon, Product, Category, Vendor, CartOrder, ProductImages, ProductReview, wishlist_model, Address

class ProductImagesAdmin(admin.TabularInline):
    model = ProductImages

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImagesAdmin]
    list_editable = ['title', 'price', 'featured', 'product_status']
    list_display = ['user', 'title', 'product_image', 'price', 'category', 'vendor', 'featured', 'product_status', 'pid']

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'category_image']

class VendorAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor_image']


class CartOrderAdmin(admin.ModelAdmin):
    list_editable = ['paid_status', 'product_status', 'sku']
    list_display = ['user',  'price', 'paid_status', 'order_date','product_status', 'sku', 'payment_method', 'khqr_status', 'khqr_reference', 'khqr_proof_image']
    list_filter = ['paid_status', 'payment_method', 'khqr_status']
    search_fields = ['oid', 'khqr_reference', 'email']
    actions = ['approve_khqr_payments', 'reject_khqr_payments']

    @admin.action(description="Approve KHQR payment and mark as paid")
    def approve_khqr_payments(self, request, queryset):
        updated = queryset.update(khqr_status="approved", paid_status=True)
        self.message_user(request, f"{updated} order(s) approved and marked as paid.")

    @admin.action(description="Reject KHQR payment")
    def reject_khqr_payments(self, request, queryset):
        updated = queryset.update(khqr_status="rejected", paid_status=False)
        self.message_user(request, f"{updated} order(s) rejected.")

    def save_model(self, request, obj, form, change):
        # Ticking `paid status` by hand would otherwise leave a KHQR order
        # reading "Paid" and "Pending Verification" at the same time.
        if obj.payment_method == "khqr" and obj.khqr_status in ("pending", "rejected") and obj.paid_status:
            obj.khqr_status = "approved"
        super().save_model(request, obj, form, change)


class CartOrderProductsAdmin(admin.ModelAdmin):
    list_display = ['order', 'invoice_no', 'item', 'image','qty', 'price', 'total']


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'review', 'rating']


class wishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'date']


class AddressAdmin(admin.ModelAdmin):
    list_editable = ['address', 'status']
    list_display = ['user', 'address', 'status']


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(CartOrder, CartOrderAdmin)
admin.site.register(CartOrderProducts, CartOrderProductsAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(wishlist_model, wishlistAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Coupon)
