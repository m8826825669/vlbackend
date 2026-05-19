from django.urls import path
from . import views

urlpatterns = [
    path('my/',                              views.my_licenses,         name='my_licenses'),
    path('validate/',                        views.validate_license,    name='validate_license'),
    path('admin/',                           views.admin_licenses,      name='admin_licenses'),
    path('<uuid:license_id>/',               views.license_detail,      name='license_detail'),
    path('<uuid:license_id>/activations/',   views.license_activations, name='license_activations'),
    path('<uuid:license_id>/deactivate/',    views.deactivate_machine,  name='deactivate_machine'),
]
