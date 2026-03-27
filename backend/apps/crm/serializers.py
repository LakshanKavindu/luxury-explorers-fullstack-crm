"""
CRM serializers: Company and Contact.

Validation layer strategy
─────────────────────────
Validation is split across three layers intentionally:

  1. Model field validators (apps/crm/models.py)
     ↳ validate_phone() — always runs regardless of which serializer is used.
       This is the last line of defence before the DB.

  2. Serializer field-level validators (validate_<field> methods)
     ↳ Business rules that need the request context (e.g., the company the
       contact belongs to, the organization for name uniqueness checks).
       These run after field deserialization but before object creation.

  3. Serializer-level cross-field validator (validate() method)
     ↳ Rules that span multiple fields or require the full deserialized data set.

Why organization is NOT accepted from the client
─────────────────────────────────────────────────
  `organization` is excluded from every writable serializer field list.
  The view's perform_create() (via TenantScopedMixin) stamps it from
  request.user.organization.  If we allowed the client to send it, a
  malicious user could POST organization=<other-org-uuid> and create
  records in another tenant's namespace.  Blocking it at the serializer
  layer means this can never happen even if a permission check has a bug.

Why `company` for Contact is a PrimaryKeyRelatedField, not a nested write
──────────────────────────────────────────────────────────────────────────
  Nested writes add complexity and allow the client to specify which company
  to link to. We use a PrimaryKeyRelatedField whose queryset is scoped to
  the requesting user's organization in __init__, so a client cannot link
  a contact to a company they don't own.
"""
from __future__ import annotations

import re
from rest_framework import serializers
from apps.crm.models import Company, Contact


# ─────────────────────────────────────────────────────────────────────────────
# Company
# ─────────────────────────────────────────────────────────────────────────────

class CompanySerializer(serializers.ModelSerializer):
    """
    Read + write serializer for Company.

    Read fields:
        logo_url  — pre-signed S3 URL generated at serialization time.
                    The raw `logo` field (S3 key path) is write-only so
                    clients only ever see the resolved URL, not the key.

    Write exclusions:
        organization  — stamped by the view from request.user.organization.
        is_deleted    — only toggled by the soft-delete endpoint; never by
                        the client directly.
        created_at, updated_at — server-managed timestamps.
    """

    # Read-only computed URL for the logo
    logo_url = serializers.SerializerMethodField(
        help_text="Pre-signed S3 URL for the logo. Null if no logo uploaded.",
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "industry",
            "country",
            "logo",          # write-only (ImageField accepts file upload)
            "logo_url",      # read-only computed URL
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_deleted", "created_at", "updated_at", "logo_url"]
        extra_kwargs = {
            # logo is write-only: clients upload a file, but never get the raw key back
            "logo": {"write_only": True, "required": False},
        }

    # ── Field validators ──────────────────────────────────────────────────────

    def validate_name(self, value: str) -> str:
        """
        Enforce per-org company name uniqueness at the serializer layer.

        Why here and not only in the DB constraint?
        The DB constraint raises an IntegrityError which DRF converts to a
        generic 400.  Catching it here gives a human-readable error message
        and lets us return it in the standard { errors: { name: [...] } } shape.
        """
        request = self.context.get("request")
        if not request:
            return value

        qs = Company.objects.filter(
            organization=request.user.organization,
            name__iexact=value,     # case-insensitive check
            is_deleted=False,
        )
        # On update, exclude the current instance
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "A company with this name already exists in your organization."
            )
        return value

    # ── Computed fields ───────────────────────────────────────────────────────

    def get_logo_url(self, obj: Company) -> str | None:
        """
        Returns the logo URL.

        In production (S3 + AWS_QUERYSTRING_AUTH=True):
            obj.logo.url generates a pre-signed URL with a time-limited
            signature.  The bucket is private; direct S3 access is blocked.

        In development (local storage):
            obj.logo.url returns the local media URL.

        Returns None if no logo has been uploaded.
        """
        if not obj.logo:
            return None
        request = self.context.get("request")
        try:
            url = obj.logo.url
            # Build absolute URL only for local storage (S3 URLs are already absolute)
            if request and not url.startswith("http"):
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None


class CompanyListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views — omits logo binary, include logo_url.
    Reduces response payload on paginated lists.
    """

    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ["id", "name", "industry", "country", "logo_url", "created_at"]
        read_only_fields = fields

    def get_logo_url(self, obj: Company) -> str | None:
        if not obj.logo:
            return None
        try:
            return obj.logo.url
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Contact
# ─────────────────────────────────────────────────────────────────────────────

class ContactSerializer(serializers.ModelSerializer):
    """
    Read + write serializer for Contact.

    Tenant-scoped company field:
        `company` is a PrimaryKeyRelatedField whose queryset is filtered to
        the requesting user's organization in __init__().  This means a client
        cannot specify a company from a different tenant — the FK lookup will
        simply fail with a validation error ("Invalid pk").

    organization exclusion:
        NOT in fields.  Set automatically by the view from
        company.organization, ensuring it always matches the company's org.

    Email uniqueness:
        Checked at the serializer layer (validate_email) against the specific
        company so the error message is clear.  The DB partial UniqueConstraint
        is the final guarantee.

    Phone validation:
        The model-level validate_phone validator runs automatically.
        The serializer's validate_phone adds an extra blank-friendly check
        (empty string is allowed; only non-empty values must be digits).
    """

    # Nested read representation of the company (id + name)
    company_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id",
            "company",          # write: UUID PK
            "company_detail",   # read: nested {id, name}
            "full_name",
            "email",
            "phone",
            "role",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_deleted", "created_at", "updated_at", "company_detail"]
        extra_kwargs = {
            "company": {"write_only": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            # Scope the company queryset to the requesting user's organization.
            # A client cannot assign a contact to a company they don't own.
            self.fields["company"].queryset = Company.objects.filter(
                organization=request.user.organization,
                is_deleted=False,
            )

    # ── Field validators ──────────────────────────────────────────────────────

    def validate_email(self, value: str) -> str:
        """
        1. Normalise to lowercase.
        2. Check uniqueness within the same company (active contacts only).

        Why at the serializer layer:
          The DB has a partial UniqueConstraint but it raises IntegrityError,
          not a clean 400.  Catching it here produces:
              { "errors": { "email": ["A contact with this email already exists..."] } }
          which the frontend can display inline on the form field.

        The company value comes from validated_data — but during field-level
        validation, other fields may not yet be deserialized.  We access the
        raw initial_data["company"] for the company PK lookup instead.
        """
        value = value.lower().strip()

        # Resolve the company from raw input (validated_data may not be ready)
        request = self.context.get("request")
        company_id = self.initial_data.get("company")

        if company_id and request:
            qs = Contact.objects.filter(
                company_id=company_id,
                organization=request.user.organization,
                email__iexact=value,
                is_deleted=False,
            )
            # On update, exclude the current instance
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    "A contact with this email already exists in this company."
                )
        return value

    def validate_phone(self, value: str) -> str:
        """
        Allow blank/empty phone (field is optional).
        Non-empty values must match \\d{8,15} exactly.
        The model-level validator also runs, but we produce a cleaner message here.
        """
        if not value:
            return value
        if not re.fullmatch(r"\d{8,15}", value):
            raise serializers.ValidationError(
                "Phone must be 8–15 digits with no spaces, dashes, or symbols."
            )
        return value

    # ── Computed fields ───────────────────────────────────────────────────────

    def get_company_detail(self, obj: Contact) -> dict:
        """Lightweight nested company for read responses."""
        return {
            "id": str(obj.company_id),
            "name": obj.company.name,
        }

    # ── Create override ───────────────────────────────────────────────────────

    def create(self, validated_data: dict) -> Contact:
        """
        Stamp organization from the company's organization.
        This ensures the denormalized organization FK always matches the
        company's actual org — it cannot be set differently by the client.
        """
        company: Company = validated_data["company"]
        validated_data["organization"] = company.organization
        return super().create(validated_data)

    def update(self, instance: Contact, validated_data: dict) -> Contact:
        """
        If the company changes on update, re-stamp the organization.
        Guards against a client moving a contact to a different company
        within the same org (valid) while keeping the org consistent.
        """
        if "company" in validated_data:
            validated_data["organization"] = validated_data["company"].organization
        return super().update(instance, validated_data)


class ContactListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views — used inside CompanyDetailSerializer
    and the paginated contact list endpoint.
    """

    class Meta:
        model = Contact
        fields = ["id", "full_name", "email", "phone", "role", "created_at"]
        read_only_fields = fields
