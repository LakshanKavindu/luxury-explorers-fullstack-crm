"""
Custom permission classes for role-based access control.

Usage in ViewSets:
    permission_classes = [IsAuthenticated, IsAdminRole]
    
Or map per-action:
    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        if self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]
"""
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Grants access only to users with role='admin'.
    Used for: DELETE operations.
    """
    message = "Only Admin users can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsManagerOrAbove(BasePermission):
    """
    Grants access to users with role='manager' or role='admin'.
    Used for: UPDATE operations.
    """
    message = "Managers or Admins can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "manager")
        )


class IsStaffOrAbove(BasePermission):
    """
    Grants access to any authenticated user with a valid role.
    Used for: CREATE operations (all roles can create).
    """
    message = "You must be authenticated with a valid role."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "manager", "staff")
        )


class IsSameOrganization(BasePermission):
    """
    Object-level check: user can only access objects in their own organization.
    This is a safety net — the queryset-level scoping in TenantScopedMixin
    already handles this for list/retrieve. Used for extra assurance on
    direct object lookups.
    """
    message = "You do not have access to this resource."

    def has_object_permission(self, request, view, obj):
        return obj.organization_id == request.user.organization_id
