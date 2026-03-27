"""
Central API v1 router.
Each app registers its own URLs here.
"""
from django.urls import path, include

urlpatterns = [
    # Auth endpoints (JWT)
    path("auth/", include("apps.accounts.urls")),

    # CRM endpoints
    path("", include("apps.crm.urls")),

    # Audit log endpoints
    path("", include("apps.audit.urls")),
]
