"""
Serializers for the accounts app.

Validation layer decisions:
  - OrganizationSerializer: read-only in all client-facing responses.
    Org creation is an admin/ops concern, not a client API operation.
  - UserSerializer: read path only. Exposes nested org so the frontend
    auth store can be populated from this response directly.
  - UserCreateSerializer: write path. Password is write_only with min_length
    enforced here (DRF layer) in addition to Django's AUTH_PASSWORD_VALIDATORS.
    organization is NEVER accepted from the request body — the view stamps it
    from request.user.organization in perform_create().
  - CustomTokenObtainPairSerializer: inlines user + org data into the JWT
    login response so the frontend can hydrate its auth store without a
    second /me round-trip.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.accounts.models import Organization, User


# ─────────────────────────────────────────────────────────────────────────────
# Organization
# ─────────────────────────────────────────────────────────────────────────────

class OrganizationSerializer(serializers.ModelSerializer):
    """
    Read-only representation of an organization.
    Nested inside UserSerializer and token responses.
    """

    class Meta:
        model = Organization
        fields = ["id", "name", "plan", "created_at"]
        read_only_fields = ["id", "name", "plan", "created_at"]


# ─────────────────────────────────────────────────────────────────────────────
# User — Read
# ─────────────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """
    Read-only user representation.
    Returned by GET /api/v1/auth/me/ and GET /api/v1/auth/users/.
    Organization is nested (not just a UUID) so the frontend gets all
    org data in one response.
    """

    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "organization", "date_joined"]
        read_only_fields = ["id", "date_joined", "organization"]


# ─────────────────────────────────────────────────────────────────────────────
# User — Write (Admin creates user within their org)
# ─────────────────────────────────────────────────────────────────────────────

class UserCreateSerializer(serializers.ModelSerializer):
    """
    Used by Admin users to create new users within their organization.

    Security decisions:
      - `organization` is NOT in `fields`. The view stamps it via perform_create().
        A client cannot POST organization=<other-org-id> to create a cross-tenant user.
      - `password` is write_only so it is never serialized in any response.
      - `role` is writable so an admin can assign roles, but the view's
        permission_classes=[IsAdminRole] ensures only admins reach this endpoint.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Minimum 8 characters. Never returned in responses.",
    )

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value: str) -> str:
        """Normalise to lowercase and ensure it isn't already taken."""
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return email

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        # organization is set by the view — not in validated_data
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Allows an Admin to update a user's full_name and role.
    Email and organization are intentionally NOT writable after creation.
    """

    class Meta:
        model = User
        fields = ["id", "full_name", "role"]
        read_only_fields = ["id"]


# ─────────────────────────────────────────────────────────────────────────────
# JWT Login — enriched token response
# ─────────────────────────────────────────────────────────────────────────────

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default simplejwt token response to embed the user profile
    and organization data alongside the access/refresh tokens.

    Why: avoids a second HTTP round-trip from the frontend after login.
    The React auth store can be fully hydrated from this single response.

    Response shape:
        {
            "access": "...",
            "refresh": "...",
            "user": {
                "id": "...",
                "email": "...",
                "full_name": "...",
                "role": "admin|manager|staff",
                "organization": {
                    "id": "...",
                    "name": "...",
                    "plan": "basic|pro"
                }
            }
        }
    """

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        user: User = self.user

        org = user.organization
        data["user"] = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization": {
                "id": str(org.id) if org else None,
                "name": org.name if org else None,
                "plan": org.plan if org else None,
            },
        }
        return data
