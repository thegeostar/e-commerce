from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from blog.models import Category, Post


def _sidebar():
    """Data every blog page's sidebar needs."""
    return {
        "blog_categories": Category.objects.all(),
        "recent_posts": Post.objects.filter(status="published")[:4],
    }


def post_list(request):
    posts = Post.objects.filter(status="published")

    query = request.GET.get("q")
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(description__icontains=query))

    paginator = Paginator(posts, 6)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "posts": page,
        "page_obj": page,
        "query": query or "",
        "heading": "Blog",
        **_sidebar(),
    }
    return render(request, "blog/post-list.html", context)


def category_post_list(request, cid):
    category = get_object_or_404(Category, cid=cid)
    posts = Post.objects.filter(status="published", category=category)

    paginator = Paginator(posts, 6)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "posts": page,
        "page_obj": page,
        "category": category,
        "query": "",
        "heading": category.title,
        **_sidebar(),
    }
    return render(request, "blog/post-list.html", context)


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status="published")

    # F() so concurrent reads can't clobber each other's increment
    Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
    post.refresh_from_db(fields=["views"])

    related = Post.objects.filter(status="published", category=post.category).exclude(pk=post.pk)[:3]

    context = {
        "post": post,
        "related_posts": related,
        **_sidebar(),
    }
    return render(request, "blog/post-detail.html", context)
