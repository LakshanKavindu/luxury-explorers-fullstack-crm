"""
URL patterns for the accounts app.
Mounted at: /api/v1/auth/

Full endpoint reference:
    POST   /api/v1/auth/token/           → Login (email + password → access + refresh + user)
    POST   /api/v1/auth/token/refresh/   → Refresh access token (send refresh, get new access)
    POST   /api/v1/auth/logout/          → Blacklist refresh token (server-side logout)
    GET    /api/v1/auth/me/              → Current user profile
    PATCH  /api/v1/auth/me/              → Update own full_name
    GET    /api/v1/auth/users/           → List org users [Admin]
    POST   /api/v1/auth/users/           → Create org user [Admin]
    GET    /api/v1/auth/users/<uuid>/    → Retrieve user [Admin]
    PATCH  /api/v1/auth/users/<uuid>/    → Update user role/name [Admin]
    DELETE /api/v1/auth/users/<uuid>/    → Deactivate user [Admin]
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    LoginView,
    LogoutView,
    MeView,
    UserListCreateView,
    UserDetailView,
)

urlpatterns = [
    # ── JWT token endpoints ───────────────────────────────────────────────────
    path(
        "token/",
        LoginView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # ── Logout ────────────────────────────────────────────────────────────────
    path(
        "logout/",
        LogoutView.as_view(),
        name="auth_logout",
    ),

    # ── Current user ──────────────────────────────────────────────────────────
    path(
        "me/",
        MeView.as_view(),
        name="auth_me",
    ),

    # ── User management (Admin only) ──────────────────────────────────────────
    path(
        "users/",
        UserListCreateView.as_view(),
        name="user_list_create",
    ),
    path(
        "users/<uuid:pk>/",
        UserDetailView.as_view(),
        name="user_detail",
    ),
]
