from rest_framework import serializers
from .models import Category, Product, PricingPlan, Testimonial


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'icon', 'description', 'product_count')

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class PricingPlanSerializer(serializers.ModelSerializer):
    discount_percent = serializers.ReadOnlyField()
    features = serializers.JSONField(source='features_included', read_only=True)

    class Meta:
        model = PricingPlan
        fields = (
            'id', 'name', 'price', 'original_price', 'discount_percent',
            'billing_cycle', 'max_users', 'max_devices',
            'features_included', 'features',
            'is_popular', 'sort_order',
        )


class TestimonialSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='author_name', read_only=True)
    role = serializers.SerializerMethodField()
    text = serializers.CharField(source='content', read_only=True)

    class Meta:
        model = Testimonial
        fields = (
            'id', 'author_name', 'author_role', 'author_company',
            'author_avatar', 'content', 'rating',
            # Friendly aliases the frontend uses:
            'name', 'role', 'text',
        )

    def get_role(self, obj):
        if obj.author_company:
            return f'{obj.author_role} · {obj.author_company}'
        return obj.author_role


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    starting_price = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    demo_type = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'emoji', 'tagline', 'description',
            'thumbnail', 'category', 'platform', 'version', 'file_size',
            'total_purchases', 'rating', 'rating_count', 'is_featured',
            'starting_price', 'tags', 'demo_type',
        )

    def get_starting_price(self, obj):
        plan = obj.plans.filter(is_active=True).order_by('price').first()
        return str(plan.price) if plan else '0'

    def get_tags(self, obj):
        """Surface up to 4 tech_stack items as tags for the listing cards."""
        if isinstance(obj.tech_stack, list):
            return obj.tech_stack[:4]
        return []

    def get_demo_type(self, obj):
        if obj.demo_video_url:
            return 'online'
        return 'request'


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    plans = PricingPlanSerializer(many=True, read_only=True)
    pricing_plans = PricingPlanSerializer(many=True, read_only=True, source='plans')
    testimonials = TestimonialSerializer(many=True, read_only=True)
    starting_price = serializers.SerializerMethodField()
    long_description = serializers.CharField(source='description', read_only=True)
    tags = serializers.SerializerMethodField()
    demo_type = serializers.SerializerMethodField()
    demo_url = serializers.URLField(source='demo_video_url', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'emoji', 'tagline',
            'description', 'long_description',
            'features', 'tech_stack', 'requirements', 'screenshots',
            'thumbnail', 'demo_video_url', 'documentation_url',
            'platform', 'version', 'file_size', 'changelog',
            'total_purchases', 'rating', 'rating_count', 'is_featured',
            'category', 'plans', 'pricing_plans', 'testimonials',
            'starting_price', 'tags', 'demo_type', 'demo_url',
            'created_at',
        )

    def get_starting_price(self, obj):
        plan = obj.plans.filter(is_active=True).order_by('price').first()
        return str(plan.price) if plan else '0'

    def get_tags(self, obj):
        if isinstance(obj.tech_stack, list):
            return obj.tech_stack
        return []

    def get_demo_type(self, obj):
        if obj.demo_video_url:
            return 'online'
        return 'request'
