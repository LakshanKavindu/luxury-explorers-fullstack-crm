"""
Root URL configuration.
All API endpoints are versioned under /api/v1/.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_router")),
]
