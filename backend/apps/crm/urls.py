"""
CRM URL configuration.

ViewSets are registered via DRF's DefaultRouter. The router generates
standard REST routes for each registered ViewSet automatically:

  Registered prefix → basename
  ──────────────────────────────
  companies          → company
  contacts           → contact

Generated route table (relative to this file's include point: /api/v1/)
────────────────────────────────────────────────────────────────────────

  Company:
    GET    /api/v1/companies/          list
    POST   /api/v1/companies/          create
    GET    /api/v1/companies/{id}/     retrieve
    PUT    /api/v1/companies/{id}/     update
    PATCH  /api/v1/companies/{id}/     partial_update
    DELETE /api/v1/companies/{id}/     destroy → soft delete (Admin only)

  Contact:
    GET    /api/v1/contacts/           list
    POST   /api/v1/contacts/           create
    GET    /api/v1/contacts/{id}/      retrieve
    PUT    /api/v1/contacts/{id}/      update
    PATCH  /api/v1/contacts/{id}/      partial_update
    DELETE /api/v1/contacts/{id}/      destroy → soft delete (Admin only)

Query parameters supported on list endpoints:
  ?search=<term>             SearchFilter — cross-field substring search
  ?industry=Technology       DjangoFilterBackend — exact field filter
  ?country=LK
  ?company=<uuid>            (contacts only)
  ?role=Engineer             (contacts only)
  ?created_after=<ISO 8601>  DateTimeFilter
  ?created_before=<ISO 8601> DateTimeFilter
  ?ordering=<field>          OrderingFilter (prefix - for descending)
  ?page=<n>&page_size=<n>    StandardPagination

Typical include in config/api_router.py:
  path("", include("apps.crm.urls"))
"""
from rest_framework.routers import DefaultRouter
from apps.crm.views import CompanyViewSet, ContactViewSet

router = DefaultRouter()

# basename is used in reverse URL lookups:
#   reverse("company-list")       → /api/v1/companies/
#   reverse("company-detail", kwargs={"pk": "<uuid>"}) → /api/v1/companies/<uuid>/
router.register(r"companies", CompanyViewSet, basename="company")
router.register(r"contacts",  ContactViewSet, basename="contact")

urlpatterns = router.urls
