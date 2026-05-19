from django.db import models
from django.conf import settings
import uuid


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    plan = models.ForeignKey('products.PricingPlan', on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')

    # Amounts in INR paise (Razorpay requirement)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Razorpay
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)

    # Billing info
    billing_name = models.CharField(max_length=200)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=15, blank=True)
    billing_address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)

    # Invoice
    invoice_number = models.CharField(max_length=20, blank=True)
    invoice_pdf = models.FileField(upload_to='invoices/', null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number} — {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random, string
            self.order_number = 'VL' + ''.join(random.choices(string.digits, k=10))
        super().save(*args, **kwargs)