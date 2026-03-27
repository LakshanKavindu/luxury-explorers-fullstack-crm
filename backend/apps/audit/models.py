"""
ActivityLog model — immutable audit trail.

Design decisions:
  - Append-only: no update/delete operations are ever performed on this table.
    The Django admin for this model is read-only; the API endpoint is GET-only.
  - organization FK → enables fast tenant-scoped audit queries without joins.
  - user SET_NULL → preserves audit records even when a user account is deleted.
    The actor's name is captured in object_repr at write time for exactly this reason.
  - object_repr → human-readable snapshot of the record at the moment of the
    action (e.g. "Acme Corp" for a Company, "John Doe <john@example.com>" for
    a Contact). Survives soft deletes and lets the log page show meaningful
    context without a JOIN.
  - Composite index on (organization, -timestamp) → the exact query used by
    the ActivityLog list endpoint (ORDER BY timestamp DESC).
"""
import uuid
from django.db import models
from django.conf import settings
from apps.accounts.models import Organization


class ActivityLog(models.Model):
    """
    Append-only audit record created on every CREATE / UPDATE / DELETE
    action performed on Company or Contact records.

    Populated from apps/crm/services.py — never created directly in views.
    This keeps the audit logic in one place and ensures it fires regardless
    of which view or serializer triggers the mutation.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    # ── Fields ────────────────────────────────────────────────────────────────

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        help_text="Tenant owner. Scopes the log to the correct organization.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_logs",
        help_text=(
            "The user who triggered the action. "
            "SET_NULL on user deletion so the log is never orphaned."
        ),
    )
    action = models.CharField(
        max_length=10,
        choices=Action.choices,
        help_text="Type of mutation: CREATE, UPDATE, or DELETE.",
    )
    model_name = models.CharField(
        max_length=50,
        help_text="Python class name of the affected model, e.g. 'Company' or 'Contact'.",
    )
    object_id = models.CharField(
        max_length=36,
        help_text="UUID (as string) of the affected record.",
    )
    object_repr = models.CharField(
        max_length=255,
        default="",
        help_text=(
            "Human-readable snapshot of the record at action time "
            "(e.g. 'Acme Corp'). Persists after soft delete."
        ),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp of the action. Set once, never modified.",
    )

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta:
        db_table = "audit_activity_logs"
        ordering = ["-timestamp"]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            # Primary query: all logs for a tenant, newest first
            models.Index(
                fields=["organization", "timestamp"],
                name="auditlog_org_timestamp_idx",
            ),
            # Filter by action type within a tenant
            models.Index(
                fields=["organization", "action"],
                name="auditlog_org_action_idx",
            ),
            # Filter by model name + object (useful for per-record history)
            models.Index(
                fields=["model_name", "object_id"],
                name="auditlog_model_object_idx",
            ),
        ]

    def __str__(self):
        actor = self.user.full_name if self.user else "Deleted User"
        return (
            f"[{self.action}] {self.model_name} '{self.object_repr}' "
            f"by {actor} at {self.timestamp:%Y-%m-%d %H:%M}"
        )
