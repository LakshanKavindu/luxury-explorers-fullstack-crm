"""
Authentication and user management views.

Endpoint map (all mounted at /api/v1/auth/):
──────────────────────────────────────────────
  POST   token/           → Login. Returns access + refresh + user profile.
  POST   token/refresh/   → Exchange a valid refresh token for a new access token.
  POST   logout/          → Blacklist the refresh token (server-side logout).
  GET    me/              → Return the currently authenticated user's profile.
  PATCH  me/              → Update own full_name only.
  GET    users/           → List users in same org [Admin only].
  POST   users/           → Create a user in same org [Admin only].
  GET    users/<id>/      → Retrieve a user [Admin only].
  PATCH  users/<id>/      → Update role / full_name [Admin only].
  DELETE users/<id>/      → Soft-deactivate a user [Admin only].

Authentication scheme:
  Every protected endpoint uses JWTAuthentication (configured globally in
  REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES). The DRF default permission
  is IsAuthenticated, so every view is protected unless explicitly set to
  AllowAny (only the token obtain and refresh endpoints).
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from apps.accounts.permissions import IsAdminRole


# ─────────────────────────────────────────────────────────────────────────────
# Login  —  POST /api/v1/auth/token/
# ─────────────────────────────────────────────────────────────────────────────

class LoginView(TokenObtainPairView):
    """
    Login with email + password.

    Returns:
        access   — short-lived JWT (2 hours). Send in Authorization header.
        refresh  — long-lived JWT (7 days). Store securely, send only to /token/refresh/.
        user     — complete user profile so the frontend auth store needs no
                   extra /me request on login.

    Authentication: AllowAny (this is the unauthenticated entry point).

    Response example:
        {
            "success": true,
            "data": {
                "access":  "eyJ...",
                "refresh": "eyJ...",
                "user": {
                    "id":        "uuid",
                    "email":     "alice@acme.com",
                    "full_name": "Alice Smith",
                    "role":      "admin",
                    "organization": {
                        "id":   "uuid",
                        "name": "Acme Corp",
                        "plan": "pro"
                    }
                }
            },
            "message": ""
        }
    """
    # TokenObtainPairView sets authentication_classes = [] and permission_classes = []
    # internally via its get_authenticators(), so this endpoint is public.
    pass   # serializer is wired via settings.SIMPLE_JWT.TOKEN_OBTAIN_SERIALIZER


# ─────────────────────────────────────────────────────────────────────────────
# Logout  —  POST /api/v1/auth/logout/
# ─────────────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    Server-side logout by blacklisting the refresh token.

    Why blacklisting is necessary:
        JWTs are stateless — the server cannot "delete" an access token once
        issued. The blacklist app (rest_framework_simplejwt.token_blacklist)
        records the refresh token's JTI (unique token ID) in the database.
        Subsequent calls to /token/refresh/ with the blacklisted token are
        rejected. The short access token lifetime (2 hours) limits the damage
        window for an already-issued access token.

    Request body:
        { "refresh": "<refresh_token>" }

    Response:
        204 No Content on success.
        400 on invalid or already-blacklisted token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request) -> Response:
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            raise InvalidToken(str(exc))

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Current User  —  GET/PATCH /api/v1/auth/me/
# ─────────────────────────────────────────────────────────────────────────────

class MeView(APIView):
    """
    GET  → Returns the authenticated user's full profile (id, email, role, org).
    PATCH → Allows the user to update their own full_name only.
            Role and email cannot be self-modified; an Admin must do that via /users/.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        # Pass request in context so nested org serializer can resolve absolute URLs if needed
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request) -> Response:
        """Self-update: only full_name is editable here."""
        user = request.user
        full_name = request.data.get("full_name", "").strip()

        if not full_name:
            return Response(
                {"detail": "full_name cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.full_name = full_name
        user.save(update_fields=["full_name"])
        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# User Management  —  Admin only
# ─────────────────────────────────────────────────────────────────────────────

class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  → List all active users in the requesting admin's organization.
    POST → Create a new user in the same organization.

    Tenant isolation:
        The queryset is manually filtered to organization=request.user.organization.
        (We don't use TenantScopedMixin here because User has nullable organization
        for superusers, and the mixin expects is_deleted.)

    Organization stamping:
        perform_create() injects organization from the request, so the client
        cannot POST organization=<other-org-uuid>  to create a cross-tenant user.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        return (
            User.objects.filter(
                organization=self.request.user.organization,
                is_active=True,
            )
            .select_related("organization")
            .order_by("full_name")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        # Stamp the organization from the requesting admin — never from request body
        serializer.save(organization=self.request.user.organization)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return the full user profile (not just the write fields) on 201
        read_serializer = UserSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Retrieve a user in the same organization.
    PATCH  → Update full_name and/or role (Admin only).
    DELETE → Soft-deactivate (sets is_active=False). Never hard deletes.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "patch", "delete", "head", "options"]  # no PUT

    def get_queryset(self):
        return User.objects.filter(
            organization=self.request.user.organization,
        ).select_related("organization")

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UserUpdateSerializer
        return UserSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True   # always partial (PATCH only)
        response = super().update(request, *args, **kwargs)
        # Return full profile after update
        read_serializer = UserSerializer(
            self.get_object(),
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft-deactivate: sets is_active=False instead of deleting the row.

        Why not hard delete:
          - The user's FK is referenced in ActivityLog. Deleting the row
            would set activity_log.user to NULL (SET_NULL), losing actor identity.
          - Deactivated users cannot log in (AbstractBaseUser checks is_active
            during authentication) but their audit trail remains intact.
        """
        user = self.get_object()

        if user == request.user:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"message": f"User '{user.full_name}' has been deactivated."},
            status=status.HTTP_200_OK,
        )
