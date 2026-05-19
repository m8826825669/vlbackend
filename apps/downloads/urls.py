from django.urls import path
from . import views

urlpatterns = [
    path('request/',      views.request_download, name='request_download'),
    path('file/<str:token>/', views.serve_download,  name='serve_download'),
    path('history/',      views.download_history,  name='download_history'),
]
