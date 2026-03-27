"""
Audit ViewSet.

ActivityLog is append-only — only GET endpoints are exposed.
Records are created exclusively by apps.audit.services.log_activity(),
called from the CRM ViewSets (apps/crm/views.py) on every mutation.

Endpoint map (all under /api/v1/activity-logs/):
─────────────────────────────────────────────────
  GET  /api/v1/activity-logs/           list   (tenant-scoped, all roles)
  GET  /api/v1/activity-logs/<id>/      retrieve (tenant-scoped, all roles)

Query parameters:
  ?action=CREATE                  ChoiceFilter (CREATE / UPDATE / DELETE)
  ?model_name=Company             iexact match
  ?object_id=<uuid>               exact object UUID — full per-record history
  ?user=<uuid>                    filter by actor UUID
  ?timestamp_after=<ISO 8601>     DateTimeFilter
  ?timestamp_before=<ISO 8601>    DateTimeFilter
  ?search=<term>                  SearchFilter on object_repr, model_name
  ?ordering=<field>               timestamp (default -timestamp), action, model_name
  ?page=<n>&page_size=<n>         StandardPagination
"""
from __future__ import annotations

from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsReadOnly, IsStaffOrAbove
from apps.audit.filters import ActivityLogFilter
from apps.audit.models import ActivityLog
from apps.audit.serializers import ActivityLogSerializer
from common.mixins import TenantScopedMixin
from common.pagination import StandardPagination


class ActivityLogViewSet(TenantScopedMixin, ReadOnlyModelViewSet):
    """
    Read-only tenant-scoped audit log endpoint.

    Security layers:
      1. ReadOnlyModelViewSet  — write action methods don't exist → 405
      2. IsReadOnly permission — HTTP method gate → 403 if bypassed somehow
      3. TenantScopedMixin     — queryset filtered to user.organization
      4. IsStaffOrAbove        — rejects unknown roles even on reads
    """

    queryset = ActivityLog.objects.select_related("user", "organization").all()
    serializer_class = ActivityLogSerializer
    pagination_class = StandardPagination

    # All three permission classes are intentional — see docstring above
    permission_classes = [IsAuthenticated, IsStaffOrAbove, IsReadOnly]

    # ── Filter / search / ordering ────────────────────────────────────────────

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_class = ActivityLogFilter

    # ?search=<term> — searches object_repr (e.g. "Acme Corp") and model_name
    search_fields = ["object_repr", "model_name"]

    # Only expose meaningful ordering columns — not internal IDs
    ordering_fields = ["timestamp", "action", "model_name"]
    ordering = ["-timestamp"]   # newest first by default
