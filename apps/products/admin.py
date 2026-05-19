from django.contrib import admin
from .models import Category, Product, PricingPlan, Testimonial

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}

class PricingPlanInline(admin.TabularInline):
    model = PricingPlan
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'version', 'total_purchases', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured', 'platform', 'category')
    search_fields = ('name', 'tagline')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PricingPlanInline]
    readonly_fields = ('total_purchases', 'rating', 'rating_count')

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'author_company', 'rating', 'is_featured')
