from django.db import models
from django.utils.text import slugify
import uuid


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    PLATFORMS = [
        ('windows', 'Windows'),
        ('mac', 'macOS'),
        ('linux', 'Linux'),
        ('all', 'All Platforms'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=10, blank=True, default='📦')
    tagline = models.CharField(max_length=300)
    description = models.TextField()
    features = models.JSONField(default=list)          # [{"title": "", "desc": "", "icon": ""}]
    tech_stack = models.JSONField(default=list)        # ["Java 21", "Spring Boot", ...]
    requirements = models.JSONField(default=dict)      # {"os": "", "ram": "", "disk": ""}
    screenshots = models.JSONField(default=list)       # [{"url": "", "caption": ""}]
    thumbnail = models.ImageField(upload_to='products/thumbnails/', null=True, blank=True)
    demo_video_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    platform = models.CharField(max_length=10, choices=PLATFORMS, default='all')
    version = models.CharField(max_length=20, default='1.0.0')
    file_size = models.CharField(max_length=20, blank=True)   # "45 MB"
    installer_file = models.FileField(upload_to='products/installers/', null=True, blank=True)
    changelog = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    total_purchases = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PricingPlan(models.Model):
    BILLING_CYCLES = [
        ('one_time', 'One Time'),
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans')
    name = models.CharField(max_length=100)     # "Starter", "Professional", "Enterprise"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLES, default='one_time')
    max_users = models.PositiveIntegerField(default=1)
    max_devices = models.PositiveIntegerField(default=1)
    features_included = models.JSONField(default=list)  # ["Feature A", "Feature B"]
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100)
        return 0


class Testimonial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='testimonials', null=True, blank=True)
    author_name = models.CharField(max_length=100)
    author_role = models.CharField(max_length=100)
    author_company = models.CharField(max_length=100, blank=True)
    author_avatar = models.ImageField(upload_to='testimonials/', null=True, blank=True)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author_name} — {self.rating}★"
