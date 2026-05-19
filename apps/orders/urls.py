from django.urls import path
from . import views


urlpatterns = [
    path('create/',          views.create_order,    name='create_order'),
    path('verify/',          views.verify_payment,  name='verify_payment'),
    path('my-orders/',       views.my_orders,       name='my_orders'),
    path('admin/',           views.admin_orders,    name='admin_orders'),
    path('<uuid:order_id>/', views.order_detail,    name='order_detail'),
]
