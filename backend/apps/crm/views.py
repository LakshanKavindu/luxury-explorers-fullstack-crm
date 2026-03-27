"""
CRM ViewSets: Company and Contact.

Full feature set
─────────────────
  ✓ Full CRUD (list, retrieve, create, update, partial_update, destroy)
  ✓ Tenant-scoped queryset via TenantScopedMixin (organization + is_deleted filter)
  ✓ Soft delete (is_deleted=True) — hard deletes are forbidden
  ✓ Pagination via StandardPagination (page / page_size query params)
  ✓ Search via SearchFilter (?search=<term> across multiple fields)
  ✓ Filtering via DjangoFilterBackend + CompanyFilter / ContactFilter
  ✓ Ordering via OrderingFilter (?ordering=<field>)
  ✓ Per-action backend permissions (Admin / Manager / Staff role matrix)
  ✓ Object-level tenant check via IsSameOrganization
  ✓ Audit logging on every CREATE / UPDATE / DELETE via log_activity()
  ✓ Versioned at /api/v1/ (set in config/urls.py → config/api_router.py)

Audit logging design
─────────────────────
  log_activity() is called explicitly in perform_create(), perform_update(),
  and destroy(). This is the service-layer approach — see apps/audit/services.py
  for a full explanation of why signals were rejected in favour of this pattern.

  Call sites:
    perform_create()  → called by DRF after serializer.save() — instance is ready
    perform_update()  → called by DRF after serializer.save() — instance is ready
    destroy()         → we control this method directly (soft delete + log)

  Failure isolation:
    log_activity() swallows its own exceptions and logs them — a failed audit
    write never rolls back the CRM mutation or surfaces a 500 to the user.

Permission matrix
──────────────────
  Action              │ Admin │ Manager │ Staff
  ────────────────────┼───────┼─────────┼──────
  list                │  ✓    │   ✓     │  ✓
  retrieve            │  ✓    │   ✓     │  ✓
  create              │  ✓    │   ✓     │  ✓
  update/partial_update│ ✓    │   ✓     │  ✗  → 403
  destroy             │  ✓    │   ✗     │  ✗  → 403

Soft delete guarantee
──────────────────────
  destroy() sets is_deleted=True and saves only that field. The row is never
  removed from the database. This preserves:
    • Contact FK back to Company (prevents dangling references)
    • ActivityLog.object_id references (audit trail must survive deletions)
  TenantScopedMixin filters is_deleted=False on every queryset, so soft-deleted
  records are invisible to all normal API responses.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import (
    IsAdminRole,
    IsManagerOrAbove,
    IsSameOrganization,
    IsStaffOrAbove,
)
from apps.audit.models import ActivityLog
from apps.audit.services import log_activity
from apps.crm.filters import CompanyFilter, ContactFilter
from apps.crm.models import Company, Contact
from apps.crm.serializers import (
    CompanyListSerializer,
    CompanySerializer,
    ContactListSerializer,
    ContactSerializer,
)
from common.mixins import TenantScopedMixin
from common.pagination import StandardPagination


# ─────────────────────────────────────────────────────────────────────────────
# Company ViewSet
# ─────────────────────────────────────────────────────────────────────────────

class CompanyViewSet(TenantScopedMixin, ModelViewSet):
    """
    Full CRUD for Company records.

    Registered at: /api/v1/companies/

    ┌──────────────────────────────────────────────────────────────────────┐
    │  Method   URL                    Action           Who                │
    ├──────────────────────────────────────────────────────────────────────┤
    │  GET      /companies/            list             All roles          │
    │  POST     /companies/            create           All roles          │
    │  GET      /companies/<id>/       retrieve         All roles          │
    │  PATCH    /companies/<id>/       partial_update   Manager, Admin     │
    │  PUT      /companies/<id>/       update           Manager, Admin     │
    │  DELETE   /companies/<id>/       destroy (soft)   Admin only         │
    └──────────────────────────────────────────────────────────────────────┘

    Query parameters
    ─────────────────
      ?search=<term>               name, industry, country (substring)
      ?industry=Technology         case-insensitive exact match
      ?country=LK                  case-insensitive exact match
      ?created_after=<ISO 8601>
      ?created_before=<ISO 8601>
      ?ordering=name               A-Z (prefix - for descending)
      ?ordering=-created_at        newest first (default)
      ?page=<n>&page_size=<n>
    """

    queryset = Company.objects.select_related("organization").all()
    pagination_class = StandardPagination

    # ── Filter / search / ordering ────────────────────────────────────────────

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CompanyFilter
    search_fields = ["name", "industry", "country"]
    ordering_fields = ["name", "created_at", "updated_at", "industry", "country"]
    ordering = ["-created_at"]

    # ── Permissions ───────────────────────────────────────────────────────────

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsManagerOrAbove(), IsSameOrganization()]
        if self.action == "retrieve":
            return [IsAuthenticated(), IsStaffOrAbove(), IsSameOrganization()]
        return [IsAuthenticated(), IsStaffOrAbove()]

    # ── Serializer selection ──────────────────────────────────────────────────

    def get_serializer_class(self):
        if self.action == "list":
            return CompanyListSerializer
        return CompanySerializer

    # ── Audit hooks ───────────────────────────────────────────────────────────

    def perform_create(self, serializer):
        """
        DRF calls this after serializer.is_valid() — we stamp org, save the
        instance, then log. Order matters: log AFTER save so instance.pk exists.
        """
        super().perform_create(serializer)          # TenantScopedMixin stamps org + saves
        log_activity(
            user=self.request.user,
            action=ActivityLog.Action.CREATE,
            instance=serializer.instance,
        )

    def perform_update(self, serializer):
        """
        DRF calls this for both PUT and PATCH. We log after super() so the
        instance reflects the updated state in object_repr.
        """
        super().perform_update(serializer)
        log_activity(
            user=self.request.user,
            action=ActivityLog.Action.UPDATE,
            instance=serializer.instance,
        )

    # ── Destroy: soft delete + audit ─────────────────────────────────────────

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: sets is_deleted=True.

        Audit log is created with the object_repr captured BEFORE the save,
        so the log shows the name of the company that was deleted even though
        it will be invisible from all queries afterwards.

        Returns 200 with a message (not 204) so the frontend can show a toast.
        """
        company = self.get_object()
        repr_snapshot = str(company)        # capture repr before soft-delete save
        company.is_deleted = True
        company.save(update_fields=["is_deleted"])
        log_activity(
            user=request.user,
            action=ActivityLog.Action.DELETE,
            instance=company,
        )
        return Response(
            {"message": f"Company '{company.name}' has been deleted."},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Contact ViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ContactViewSet(TenantScopedMixin, ModelViewSet):
    """
    Full CRUD for Contact records.

    Registered at: /api/v1/contacts/

    ┌──────────────────────────────────────────────────────────────────────┐
    │  Method   URL                    Action           Who                │
    ├──────────────────────────────────────────────────────────────────────┤
    │  GET      /contacts/             list             All roles          │
    │  POST     /contacts/             create           All roles          │
    │  GET      /contacts/<id>/        retrieve         All roles          │
    │  PATCH    /contacts/<id>/        partial_update   Manager, Admin     │
    │  PUT      /contacts/<id>/        update           Manager, Admin     │
    │  DELETE   /contacts/<id>/        destroy (soft)   Admin only         │
    └──────────────────────────────────────────────────────────────────────┘

    Query parameters
    ─────────────────
      ?search=<term>               full_name, email, role (substring)
      ?company=<uuid>              filter contacts for one company
      ?role=Engineer               case-insensitive exact match
      ?created_after=<ISO 8601>
      ?created_before=<ISO 8601>
      ?ordering=full_name          A-Z (prefix - for descending)
      ?ordering=-created_at        newest first (default)
      ?page=<n>&page_size=<n>
    """

    queryset = Contact.objects.select_related("company", "organization").all()
    pagination_class = StandardPagination

    # ── Filter / search / ordering ────────────────────────────────────────────

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ["full_name", "email", "role"]
    ordering_fields = ["full_name", "email", "role", "created_at", "updated_at"]
    ordering = ["-created_at"]

    # ── Permissions ───────────────────────────────────────────────────────────

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsManagerOrAbove(), IsSameOrganization()]
        if self.action == "retrieve":
            return [IsAuthenticated(), IsStaffOrAbove(), IsSameOrganization()]
        return [IsAuthenticated(), IsStaffOrAbove()]

    # ── Serializer selection ──────────────────────────────────────────────────

    def get_serializer_class(self):
        if self.action == "list":
            return ContactListSerializer
        return ContactSerializer

    # ── Audit hooks ───────────────────────────────────────────────────────────

    def perform_create(self, serializer):
        super().perform_create(serializer)
        log_activity(
            user=self.request.user,
            action=ActivityLog.Action.CREATE,
            instance=serializer.instance,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        log_activity(
            user=self.request.user,
            action=ActivityLog.Action.UPDATE,
            instance=serializer.instance,
        )

    # ── Destroy: soft delete + audit ─────────────────────────────────────────

    def destroy(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.is_deleted = True
        contact.save(update_fields=["is_deleted"])
        log_activity(
            user=request.user,
            action=ActivityLog.Action.DELETE,
            instance=contact,
        )
        return Response(
            {"message": f"Contact '{contact.full_name}' has been deleted."},
            status=status.HTTP_200_OK,
        )
