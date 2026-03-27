"""
CRM models: Company and Contact.

Design decisions:
  - Company.organization FK  → direct tenant key; never query without it
  - Contact.organization FK  → deliberately denormalized from Company so
    ActivityLog and tenant queries don't need a JOIN through Company
  - Soft delete (is_deleted)  → flag-based; hard deletes are forbidden so
    audit history is never orphaned
  - Partial UniqueConstraint on Contact.email  → uniqueness is enforced only
    among active (is_deleted=False) records, allowing an email to be reused
    after a contact is soft-deleted
  - Composite DB indexes on (organization, is_deleted)  → the most common
    query pattern; avoids full-table scans in large tenants
  - logo stored via django-storages → S3 in production, local FS in dev
"""
import uuid
import re
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from apps.accounts.models import Organization


# ─────────────────────────────────────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_phone(value: str) -> None:
    """
    Accepts 8–15 consecutive digit characters only.
    Rejects spaces, dashes, parentheses, and country-code prefixes like '+'.
    Frontend should strip formatting before sending.
    """
    if value and not re.fullmatch(r"\d{8,15}", value):
        raise ValidationError(
            "Phone number must contain 8–15 digits with no spaces, dashes, or symbols."
        )

def validate_image_size(image):
    """
    Validates that the uploaded image size is under 2MB.
    Ideal for AWS S3 Free Tier and fast loading times.
    """
    max_size_kb = 2048
    if image.size > max_size_kb * 1024:
        raise ValidationError(f"Image size cannot exceed {max_size_kb / 1024}MB.")


# ─────────────────────────────────────────────────────────────────────────────
# Company
# ─────────────────────────────────────────────────────────────────────────────

class Company(models.Model):
    """
    A company record owned by one organization (tenant).

    Soft delete pattern: setting is_deleted=True hides the record from all
    normal queries via TenantScopedMixin. Hard deletes are never performed
    so ActivityLog entries retain their object_id reference context.

    Logo upload:
        In development:  stored to MEDIA_ROOT/logos/
        In production:   django-storages routes to S3 (STORAGES["default"])
        Access strategy: pre-signed URLs (AWS_QUERYSTRING_AUTH=True) — the
                         bucket is private; the serializer generates a
                         time-limited URL on every read.
    """

    # ── Fields ────────────────────────────────────────────────────────────────

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="companies",
        help_text="Tenant owner. Every query MUST filter by this field.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Company display name. Unique within the organization.",
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Industry sector (e.g. 'Technology', 'Finance'). Optional.",
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Country of headquarters. ISO alpha-2 or full name. Optional.",
    )
    logo = models.ImageField(
        upload_to="logos/",
        blank=True,
        null=True,
        validators=[validate_image_size],
        help_text=(
            "Company logo. Stored on S3 in production. "
            "Served via pre-signed URLs — bucket is private. "
            "Max size: 2MB to optimize Free Tier usage."
        ),
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag. TenantScopedMixin always filters is_deleted=False.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Set once on creation. Never modified.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Updated automatically on every save().",
    )

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta:
        db_table = "crm_companies"
        ordering = ["-created_at"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        constraints = [
            # Company name must be unique per organization (not globally)
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_active_company_name_per_org",
            )
        ]
        indexes = [
            # Primary tenant query pattern: all active companies for an org
            models.Index(
                fields=["organization", "is_deleted"],
                name="company_org_deleted_idx",
            ),
            # Search / ordering by name within a tenant
            models.Index(
                fields=["organization", "name"],
                name="company_org_name_idx",
            ),
        ]

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# Contact
# ─────────────────────────────────────────────────────────────────────────────

class Contact(models.Model):
    """
    A contact person belonging to a Company.

    Email uniqueness rule:
        Enforced via a partial UniqueConstraint scoped to (company, email)
        where is_deleted=False.  This means:
          ✓  Two different companies CAN have the same email address
          ✓  A soft-deleted contact's email CAN be reused in the same company
          ✗  Two active contacts in the same company CANNOT share an email

    Organization FK:
        Denormalized from Company deliberately.  Without it, every tenant-scoped
        query on Contact would need a JOIN through Company.  The trade-off
        (slight data duplication) is worthwhile for query efficiency and for
        keeping ActivityLog queries simple.
    """

    # ── Fields ────────────────────────────────────────────────────────────────

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="contacts",
        help_text=(
            "Denormalized tenant key. Copied from company.organization on create "
            "by CompanyContactCreateSerializer. Never editable by the client."
        ),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="contacts",
        help_text="The parent company this contact belongs to.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Contact's full display name.",
    )
    email = models.EmailField(
        help_text=(
            "Must be a valid email format. "
            "Unique within the same company (partial constraint, active only)."
        ),
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        default="",
        validators=[validate_phone],
        help_text="Optional. 8–15 consecutive digits. No spaces or symbols.",
    )
    role = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Job title or role at the company. Optional free-text.",
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag. Filtered out by TenantScopedMixin.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta:
        db_table = "crm_contacts"
        ordering = ["full_name"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        constraints = [
            # Uniqueness: email must be unique per company among active contacts only
            models.UniqueConstraint(
                fields=["company", "email"],
                condition=models.Q(is_deleted=False),
                name="unique_active_contact_email_per_company",
            )
        ]
        indexes = [
            # Tenant queries: all active contacts for an org
            models.Index(
                fields=["organization", "is_deleted"],
                name="contact_org_deleted_idx",
            ),
            # Nested queries: all active contacts for a specific company
            models.Index(
                fields=["company", "is_deleted"],
                name="contact_company_deleted_idx",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"
