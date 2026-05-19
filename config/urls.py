from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/',      include('apps.accounts.urls')),
    path('api/products/',  include('apps.products.urls')),
    path('api/orders/',    include('apps.orders.urls')),
    path('api/licenses/',  include('apps.licenses.urls')),
    path('api/downloads/', include('apps.downloads.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
