from django.urls import path
from . import views

urlpatterns = [
    # ─── Public ──────────────────────────────────────────────────────────
    path('',                       views.ProductListView.as_view(),     name='product_list'),
    path('featured/',              views.featured_products,              name='featured_products'),
    path('categories/',            views.CategoryListView.as_view(),     name='category_list'),
    path('testimonials/',          views.TestimonialListView.as_view(),  name='testimonials'),
    path('stats/',                 views.site_stats,                     name='site_stats'),
    path('demo-request/',          views.demo_request,                   name='demo_request'),

    # ─── Admin ───────────────────────────────────────────────────────────
    path('admin/stats/',           views.admin_stats,                    name='admin_stats'),
    path('admin/list/',            views.AdminProductListView.as_view(), name='admin_product_list'),
    path('admin/<slug:slug>/',     views.AdminProductDetailView.as_view(), name='admin_product_detail'),
    path('<slug:slug>/upload-installer/', views.upload_installer,        name='upload_installer'),

    # ─── Public detail (KEEP LAST: catches all other slugs) ──────────────
    path('<slug:slug>/',           views.ProductDetailView.as_view(),    name='product_detail'),
]
