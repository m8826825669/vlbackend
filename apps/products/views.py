from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum

from .models import Category, Product, PricingPlan, Testimonial
from .serializers import (
    CategorySerializer, ProductListSerializer,
    ProductDetailSerializer, TestimonialSerializer,
)


# ─── PUBLIC LIST / DETAIL ───────────────────────────────────────────────────
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'platform', 'is_featured']
    search_fields = ['name', 'tagline', 'description']
    ordering_fields = ['name', 'rating', 'total_purchases', 'created_at']
    ordering = ['-is_featured', 'sort_order']

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('plans')
        )


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('plans', 'testimonials')
        )


class TestimonialListView(generics.ListAPIView):
    serializer_class = TestimonialSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Testimonial.objects.all()
        if self.request.query_params.get('featured'):
            qs = qs.filter(is_featured=True)
        return qs.order_by('-is_featured', '-created_at')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_products(request):
    products = (
        Product.objects.filter(is_active=True, is_featured=True)
        .select_related('category')
        .prefetch_related('plans')
    )
    return Response(ProductListSerializer(products, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def site_stats(request):
    from apps.orders.models import Order
    return Response({
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_customers': Order.objects.values('user').distinct().count(),
        'total_orders': Order.objects.filter(status='completed').count(),
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def demo_request(request):
    """
    Capture demo requests and email the support team.

    Frontend sends:
        { name, email, phone?, company?, product_name?, message? }
    """
    from django.conf import settings as dj_settings
    from django.core.mail import EmailMessage
    import logging
    log = logging.getLogger(__name__)

    name         = (request.data.get('name') or '').strip()
    email        = (request.data.get('email') or '').strip()
    phone        = (request.data.get('phone') or '').strip()
    company      = (request.data.get('company') or '').strip()
    product_name = (request.data.get('product_name') or 'a product').strip()
    user_message = (request.data.get('message') or '').strip()

    if not name or not email:
        return Response(
            {'detail': 'Name and email are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    site_name     = getattr(dj_settings, 'SITE_NAME', 'Vexen Labs')
    support_email = getattr(dj_settings, 'SUPPORT_EMAIL', 'support@vexenlabs.com')

    body_lines = [
        f"New demo request from {site_name}.",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  CONTACT",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Name    : {name}",
        f"Email   : {email}",
        f"Phone   : {phone or '(not provided)'}",
        f"Company : {company or '(not provided)'}",
        f"Product : {product_name}",
        "",
    ]
    if user_message:
        body_lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "  MESSAGE",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            user_message,
            "",
        ]

    try:
        EmailMessage(
            subject=f"[Demo Request] {product_name} — {name}",
            body="\n".join(body_lines),
            from_email=dj_settings.DEFAULT_FROM_EMAIL,
            to=[support_email],
            reply_to=[f"{name} <{email}>"],
        ).send()
        log.info(f"Demo request: {email} → {product_name}")
        return Response({
            'detail': "Thanks! Our team will reach out within 24 hours to schedule your demo.",
        })
    except Exception as exc:
        log.error(f"Demo request email failed: {exc}")
        return Response(
            {'detail': f'Failed to send. Please email {support_email} directly.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ─── ADMIN ─────────────────────────────────────────────────────────────────
class AdminProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Extends admin detail to accept multipart (installer file uploads)."""
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def upload_installer(request, slug):
    """Upload/replace the installer file for a product (admin only).

    Frontend: adminAPI.uploadInstaller(slug, FormData)
    Body: multipart/form-data with field `installer_file` (or `file`)
    """
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    f = request.FILES.get('installer_file') or request.FILES.get('file')
    if not f:
        return Response(
            {'detail': 'No file provided (expected field "installer_file").'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product.installer_file = f
    # Auto-fill version/file_size if provided
    version = request.data.get('version')
    if version:
        product.version = version
    file_size = request.data.get('file_size') or _human_size(f.size)
    product.file_size = file_size
    product.save()

    return Response({
        'detail': 'Installer uploaded successfully.',
        'slug': product.slug,
        'version': product.version,
        'file_size': product.file_size,
        'url': request.build_absolute_uri(product.installer_file.url),
    })


def _human_size(num_bytes: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024:
            return f'{num_bytes:.0f} {unit}'
        num_bytes /= 1024
    return f'{num_bytes:.1f} TB'


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_stats(request):
    """Dashboard summary for admin panel."""
    from apps.orders.models import Order
    from apps.licenses.models import License
    from apps.accounts.models import User

    completed = Order.objects.filter(status='completed')
    revenue = completed.aggregate(total=Sum('total_amount'))['total'] or 0

    return Response({
        'total_products': Product.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'total_orders': Order.objects.count(),
        'completed_orders': completed.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'total_revenue': float(revenue),
        'total_licenses': License.objects.count(),
        'active_licenses': License.objects.filter(is_active=True).count(),
        'total_users': User.objects.count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
    })