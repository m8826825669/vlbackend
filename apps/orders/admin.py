from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'plan', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('order_number', 'user__email', 'billing_email', 'razorpay_payment_id')
    readonly_fields = ('id', 'order_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)
