from django.db import models
from django.conf import settings
import uuid, secrets, string


class License(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='licenses')
    order = models.OneToOneField('orders.Order', on_delete=models.PROTECT, related_name='license')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='licenses')
    plan = models.ForeignKey('products.PricingPlan', on_delete=models.PROTECT, related_name='licenses')
    license_key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    max_activations = models.PositiveIntegerField(default=1)
    activation_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)  # None = lifetime
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.license_key[:16]}... — {self.user.email}"

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired


class LicenseActivation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='activations')
    machine_id = models.CharField(max_length=128)
    machine_name = models.CharField(max_length=200, blank=True)
    os_info = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['license', 'machine_id']

    def __str__(self):
        return f"{self.license.license_key[:8]}... on {self.machine_name}"
