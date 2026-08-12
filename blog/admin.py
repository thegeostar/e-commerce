from django.contrib import admin

from blog.models import Category, Post


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'post_count']


class PostAdmin(admin.ModelAdmin):
    list_editable = ['title', 'category', 'featured', 'status']
    list_display = ['post_image', 'title', 'user', 'category', 'featured', 'status', 'views', 'date']
    list_filter = ['status', 'featured', 'category']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}


admin.site.register(Category, CategoryAdmin)
admin.site.register(Post, PostAdmin)
