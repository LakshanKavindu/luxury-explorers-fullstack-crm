"""
Serializers for the audit app.

ActivityLog is append-only — no write serializer is needed.
The read serializer is used by the GET /api/v1/activity-logs/ endpoint only.

Validation notes:
  - No validation is needed here because ActivityLog records are NEVER
    created by client input. They are created exclusively by the service
    layer (apps/crm/services.py) on successful Company/Contact mutations.
  - The serializer is therefore 100% read-only.

Tenant scoping:
  - The ActivityLogViewSet applies TenantScopedMixin, which filters
    organization=request.user.organization before returning any records.
    The serializer itself does not need to enforce this — it trusts the
    queryset it receives from the view.
"""
from rest_framework import serializers
from apps.audit.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for ActivityLog entries.

    Fields:
        user_display    — actor's full name (or "Deleted User" if account removed).
                          Computed from the FK so the log page never shows a raw UUID.
        action_display  — human label for the action choice (e.g. "Create").
        model_name      — Python class name of the affected resource.
        object_id       — UUID string of the affected record.
        object_repr     — human-readable snapshot captured at write time
                          (e.g. "Acme Corp", "John Doe <john@acme.com>").
                          Remains meaningful even after soft delete.
        timestamp       — ISO 8601 UTC timestamp of the action.
    """

    # Actor display — avoids exposing the raw user FK UUID in the response
    user_display = serializers.SerializerMethodField(
        help_text="Full name of the user who performed the action, or 'Deleted User'.",
    )

    # Human-readable action label (uses TextChoices .label)
    action_display = serializers.SerializerMethodField(
        help_text="Human-readable action label: Create, Update, or Delete.",
    )

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user_display",
            "action",
            "action_display",
            "model_name",
            "object_id",
            "object_repr",
            "timestamp",
        ]
        read_only_fields = fields   # every field is read-only

    def get_user_display(self, obj: ActivityLog) -> str:
        if obj.user:
            return obj.user.full_name
        return "Deleted User"

    def get_action_display(self, obj: ActivityLog) -> str:
        return obj.get_action_display()
