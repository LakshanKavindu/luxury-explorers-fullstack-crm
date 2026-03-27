"""
FilterSet for ActivityLog list endpoint.

Supported query parameters
───────────────────────────
  ?action=CREATE                   exact action type (CREATE / UPDATE / DELETE)
  ?model_name=Company              case-insensitive exact model name
  ?object_id=<uuid>               exact object UUID (per-record history)
  ?user=<uuid>                    filter by actor user UUID
  ?timestamp_after=2024-01-01T00:00:00Z
  ?timestamp_before=2024-12-31T23:59:59Z
  ?search=acme                    cross-field search (object_repr, model_name)
  ?ordering=-timestamp            newest first (default)
  ?ordering=action                alphabetical by action type
"""
import django_filters
from apps.audit.models import ActivityLog


class ActivityLogFilter(django_filters.FilterSet):

    # Action type: CREATE, UPDATE, or DELETE (exact TextChoices value)
    action = django_filters.ChoiceFilter(
        choices=ActivityLog.Action.choices,
        label="Filter by action type (CREATE, UPDATE, DELETE)",
    )

    # Model name: Company or Contact (case-insensitive)
    model_name = django_filters.CharFilter(
        field_name="model_name",
        lookup_expr="iexact",
        label="Filter by affected model name (e.g. Company, Contact)",
    )

    # Per-record history: all audit events for one specific object
    object_id = django_filters.UUIDFilter(
        field_name="object_id",
        label="Filter by affected object UUID",
    )

    # Filter by actor — useful for per-user audit reviews
    user = django_filters.UUIDFilter(
        field_name="user__id",
        label="Filter by actor user UUID",
    )

    # Date-range filters — both ends optional (open-ended ranges are fine)
    timestamp_after = django_filters.DateTimeFilter(
        field_name="timestamp",
        lookup_expr="gte",
        label="Return logs on or after this datetime (ISO 8601)",
    )
    timestamp_before = django_filters.DateTimeFilter(
        field_name="timestamp",
        lookup_expr="lte",
        label="Return logs on or before this datetime (ISO 8601)",
    )

    class Meta:
        model = ActivityLog
        fields = [
            "action",
            "model_name",
            "object_id",
            "user",
            "timestamp_after",
            "timestamp_before",
        ]
