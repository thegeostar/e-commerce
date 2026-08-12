from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.text import slugify
from shortuuid.django_fields import ShortUUIDField
from django_ckeditor_5.fields import CKEditor5Field

from userauths.models import User

STATUS = (
    ("draft", "Draft"),
    ("disabled", "Disabled"),
    ("in_review", "In Review"),
    ("published", "Published"),
)


class Category(models.Model):
    cid = ShortUUIDField(unique=True, length=10, max_length=20,
                         prefix="blogcat", alphabet="abcdefgh12345")
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to="blog", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Blog Categories"

    def post_count(self):
        return self.posts.filter(status="published").count()

    def __str__(self):
        return self.title


class Post(models.Model):
    bid = ShortUUIDField(unique=True, length=10, max_length=20,
                         prefix="post", alphabet="abcdefgh12345")

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    image = models.ImageField(upload_to="blog", null=True, blank=True)

    # short teaser shown on the listing page
    description = models.TextField(null=True, blank=True)
    content = CKEditor5Field(config_name="extends", null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="posts")

    status = models.CharField(choices=STATUS, max_length=10, default="published")
    featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)

    date = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(null=True, blank=True, auto_now=True)

    class Meta:
        ordering = ["-date"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "post"
            slug = base
            n = 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:post-detail", args=[self.slug])

    def post_image(self):
        if self.image:
            return mark_safe('<img src="%s" width="50" height="50" />' % self.image.url)
        return ""

    def __str__(self):
        return self.title
