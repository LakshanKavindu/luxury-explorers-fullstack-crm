"""
Shared ViewSet mixin that enforces tenant isolation on every query.

Usage:
    class CompanyViewSet(TenantScopedMixin, ModelViewSet):
        queryset = Company.objects.all()
        ...

The mixin:
  1. Filters queryset to the authenticated user's organization
  2. Excludes soft-deleted records (is_deleted=False)
  3. Automatically stamps `organization` on create
"""
from rest_framework.exceptions import PermissionDenied


class TenantScopedMixin:
    """
    Restricts all queryset access to the current user's organization.
    Applied as the first mixin so get_queryset() is always scoped.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        # Scope to tenant; exclude soft-deleted records
        qs = qs.filter(organization=user.organization)

        # Only apply is_deleted filter if the model has that field
        if hasattr(qs.model, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        return qs

    def perform_create(self, serializer):
        """Automatically set organization from the authenticated user."""
        serializer.save(organization=self.request.user.organization)
