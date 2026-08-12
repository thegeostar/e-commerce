from django.urls import path

from blog.views import category_post_list, post_detail, post_list

app_name = "blog"

urlpatterns = [
    path("", post_list, name="post-list"),
    path("category/<cid>/", category_post_list, name="category-post-list"),
    path("<slug:slug>/", post_detail, name="post-detail"),
]
