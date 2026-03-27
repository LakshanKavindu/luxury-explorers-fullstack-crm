"""
Audit URL configuration.

Router-registered routes (prefix /api/v1/):

  activity-logs/
    GET  /api/v1/activity-logs/         → list     (all roles — tenant-scoped)
    GET  /api/v1/activity-logs/<id>/    → retrieve (all roles — tenant-scoped)

No write routes are registered. ActivityLog is append-only; records are
created by the CRM service layer, never by client requests.
"""
from rest_framework.routers import DefaultRouter
from apps.audit.views import ActivityLogViewSet

router = DefaultRouter()
router.register(r"activity-logs", ActivityLogViewSet, basename="activitylog")

urlpatterns = router.urls
