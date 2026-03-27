"""
Organization and User models.

Design decisions:
  - UUID primary keys on every model  → prevents integer enumeration attacks
  - AbstractBaseUser + PermissionsMixin → full control over login field (email)
  - Role stored as a CharField on User → 3 roles don't warrant a separate table;
    TextChoices keeps it type-safe and migratable
  - Organization FK on User → enforced at DB level, not just application level
  - is_admin / is_manager properties → permission classes can call user.is_admin
    instead of comparing strings everywhere
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from apps.accounts.managers import UserManager


# ─────────────────────────────────────────────────────────────────────────────
# Organization
# ─────────────────────────────────────────────────────────────────────────────

class Organization(models.Model):
    """
    A tenant in the multi-tenant system.

    Every CRM record (Company, Contact, ActivityLog) carries a FK back to this
    model.  Row-based tenancy: all tenants share the same DB schema but data is
    partitioned by organization_id at the query layer (TenantScopedMixin).
    """

    class Plan(models.TextChoices):
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"

    # ── Fields ────────────────────────────────────────────────────────────────

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID PK. Not auto-incremented so tenant IDs cannot be guessed.",
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Display name of the organization. Must be globally unique.",
    )
    plan = models.CharField(
        max_length=10,
        choices=Plan.choices,
        default=Plan.BASIC,
        help_text="Subscription tier. Drives feature gating in future iterations.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Immutable creation timestamp set by the database.",
    )

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta:
        db_table = "organizations"
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return f"{self.name} ({self.get_plan_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.

    Uses email as the login credential instead of a username field.
    Extends AbstractBaseUser so we have full control over authentication;
    PermissionsMixin adds the Django groups/permissions infrastructure needed
    for the Admin site.

    Role assignment:
        admin   → full CRUD including delete
        manager → create + update, no delete
        staff   → read + create only
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"

    # ── Fields ────────────────────────────────────────────────────────────────

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,   # null=True permits creating a Django superuser without an org
        blank=True,
        help_text="The tenant this user belongs to. Null only for Django superusers.",
    )
    email = models.EmailField(
        unique=True,
        help_text="Primary login credential. Unique across the entire system.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Display name shown in the UI and audit logs.",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STAFF,
        help_text="Determines what actions the user can perform (RBAC).",
    )

    # Django internals
    is_active = models.BooleanField(
        default=True,
        help_text="Soft-deactivation flag. Deactivated users cannot log in.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Grants access to the /admin/ site. Not related to the 'Staff' role.",
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
    )

    # ── Manager + Auth config ─────────────────────────────────────────────────

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta:
        db_table = "users"
        ordering = ["full_name"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}> [{self.role}]"

    # ── Convenience properties (used by permission classes) ───────────────────

    @property
    def is_admin(self) -> bool:
        """True for Admin role only."""
        return self.role == self.Role.ADMIN

    @property
    def is_manager_or_above(self) -> bool:
        """True for Admin and Manager roles."""
        return self.role in (self.Role.ADMIN, self.Role.MANAGER)
