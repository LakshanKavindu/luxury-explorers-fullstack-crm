"""
Custom DRF permission classes for role-based access control (RBAC).

Role matrix
───────────
  Role      │ LIST  │ RETRIEVE │ CREATE │ UPDATE │ DELETE
  ──────────┼───────┼──────────┼────────┼────────┼────────
  Admin     │  ✓    │    ✓     │   ✓    │   ✓    │   ✓
  Manager   │  ✓    │    ✓     │   ✓    │   ✓    │   ✗
  Staff     │  ✓    │    ✓     │   ✓    │   ✗    │   ✗

Staff write access rationale
──────────────────────────────
  Staff can CREATE new companies and contacts. This reflects on-the-ground CRM
  usage: a sales agent (staff) needs to log new leads and contacts they
  encounter. What they cannot do is retroactively edit existing records
  (UPDATE) or remove them (DELETE). Modifications and removals are managerial
  decisions.

  A stricter interpretation (staff = read-only) would force all data entry
  through managers, which is impractical for a sales-facing CRM.

Usage in ViewSets
──────────────────
  Option A — use get_permissions() for per-action granularity (recommended):

      def get_permissions(self):
          if self.action == 'destroy':
              return [IsAuthenticated(), IsAdminRole()]
          if self.action in ('update', 'partial_update'):
              return [IsAuthenticated(), IsManagerOrAbove()]
          if self.action == 'create':
              return [IsAuthenticated(), IsStaffOrAbove()]
          return [IsAuthenticated(), IsSameOrganization()]

  Option B — use CRMActionPermission as a single catch-all class (convenience):

      permission_classes = [IsAuthenticated, CRMActionPermission]

Object-level permissions
──────────────────────────
  IsSameOrganization.has_object_permission() is a safety net on top of the
  queryset-level scoping in TenantScopedMixin. Both must be present. Neither
  alone is sufficient:

    • Without queryset scoping  → list endpoints expose all tenants' data.
    • Without object permission → a crafted URL like /companies/<other-org-uuid>/
      might bypass the queryset if get_queryset() is overridden incorrectly.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


# ─────────────────────────────────────────────────────────────────────────────
# Role-based permission classes
# ─────────────────────────────────────────────────────────────────────────────

class IsAdminRole(BasePermission):
    """
    Grants access only to users with role='admin'.

    Use for: DELETE operations, user management.
    Returns 403 with a clear message so the frontend can show a meaningful error.
    """
    message = "Only Admin users can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsManagerOrAbove(BasePermission):
    """
    Grants access to users with role='manager' or role='admin'.

    Use for: UPDATE (PUT/PATCH) operations.
    Staff cannot edit existing records — they can only create.
    """
    message = "Only Managers or Admins can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "manager")
        )


class IsStaffOrAbove(BasePermission):
    """
    Grants access to any authenticated user with a valid CRM role.

    Use for: CREATE and LIST/RETRIEVE operations (all roles can read and create).
    This is a semantic alias to IsAuthenticated scoped to role-carrying users.
    It also guards against a hypothetical future role (e.g. 'viewer') that
    should not be able to create records.
    """
    message = "You must have a valid CRM role to perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "manager", "staff")
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tenant isolation — object level
# ─────────────────────────────────────────────────────────────────────────────

class IsSameOrganization(BasePermission):
    """
    Object-level check: ensures the object being accessed belongs to the same
    organization as the requesting user.

    This is the second layer of tenant isolation (first is get_queryset() in
    TenantScopedMixin). Both must be active. Relying on only one creates a
    single point of failure.

    Safe methods (GET, HEAD, OPTIONS) pass through here — they rely on the
    queryset being already scoped. Mutating methods get the same check.

    Uses organization_id (the raw FK integer/UUID) rather than organization
    (the full related object) to avoid an extra DB query.
    """
    message = "You do not have access to this resource."

    def has_object_permission(self, request, view, obj) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(obj, "organization_id", None) == request.user.organization_id
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: single permission class for CRM ViewSets
# ─────────────────────────────────────────────────────────────────────────────

class CRMActionPermission(BasePermission):
    """
    Combines role checking AND tenant isolation into a single permission class.

    Enforces the full role matrix in one place:
      - DELETE              → Admin only
      - PUT / PATCH         → Manager or above
      - POST (create)       → Staff or above (all roles)
      - GET / HEAD / OPTIONS → Staff or above (all roles)
      - Object-level        → IsSameOrganization check on all non-safe detail routes

    Why use this over individual permission classes?
      Convenience. Instead of wiring get_permissions() in every ViewSet, you
      can set:
          permission_classes = [IsAuthenticated, CRMActionPermission]

      The trade-off: slightly less explicit than per-action get_permissions(),
      but still fully enforced on the backend. Choose whichever style fits
      your team's preference — both are correct.

    Note: has_permission() runs BEFORE get_object() (no object available).
          has_object_permission() runs AFTER get_object() (object available).
          DRF calls has_object_permission() only for retrieve/update/destroy.
    """
    message = "You do not have permission to perform this action."

    # Roles allowed to call any endpoint at all
    _VALID_ROLES = ("admin", "manager", "staff")

    def has_permission(self, request, view) -> bool:
        """View-level gate: runs before the object is fetched."""
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Reject unknown roles early
        if user.role not in self._VALID_ROLES:
            self.message = "Your account role is not recognized."
            return False

        action = getattr(view, "action", None)

        # DELETE → Admin only
        if action == "destroy":
            if user.role != "admin":
                self.message = "Only Admins can delete records."
                return False

        # UPDATE (full or partial) → Manager or above
        elif action in ("update", "partial_update"):
            if user.role not in ("admin", "manager"):
                self.message = "Only Managers or Admins can update records."
                return False

        # CREATE / LIST / RETRIEVE → all valid roles pass
        # (Staff can create and read)

        return True

    def has_object_permission(self, request, view, obj) -> bool:
        """Object-level gate: runs after get_object() fetches the record."""
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Tenant isolation: object must belong to the user's organization
        obj_org_id = getattr(obj, "organization_id", None)
        if obj_org_id != user.organization_id:
            self.message = "You do not have access to this resource."
            return False

        return True


# ─────────────────────────────────────────────────────────────────────────────
# ActivityLog — read-only guard
# ─────────────────────────────────────────────────────────────────────────────

class IsReadOnly(BasePermission):
    """
    Allows only safe HTTP methods: GET, HEAD, OPTIONS.

    Apply to ActivityLogViewSet to enforce its append-only nature at the
    HTTP layer — even if someone accidentally wires a write route, this
    class will block it with a 403 before it touches the database.

    This is belt-and-suspenders alongside using ReadOnlyModelViewSet,
    which already disables the write action methods entirely. Using both:
      1. ReadOnlyModelViewSet  → write action methods don't exist → 405 Method Not Allowed
      2. IsReadOnly permission → even if a write method somehow slips through → 403

    Using ReadOnlyModelViewSet alone is sufficient in practice. IsReadOnly
    is the extra guard for defence-in-depth.
    """
    message = "Activity logs are read-only."

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS
