"""
FilterSet classes for CRM models.

Provides field-level filtering on Company and Contact via django-filter.
These are wired into the ViewSets via filterset_class — DRF's DjangoFilterBackend
picks them up automatically alongside SearchFilter and OrderingFilter.

Why separate file?
  Keeps views.py focused on HTTP concerns (routing, permissions, response shaping).
  FilterSet logic can grow independently (date ranges, multi-value filters, etc.)
  without touching the ViewSet.

Query parameter examples
─────────────────────────
  Company:
    ?industry=Technology          exact match (case-sensitive)
    ?industry__icontains=tech     partial match
    ?country=LK
    ?search=acme                  cross-field search (name, industry, country)
    ?ordering=-created_at         sort by newest first
    ?ordering=name                sort by name A-Z
    ?page=2&page_size=10          pagination

  Contact:
    ?company=<uuid>               filter contacts for one company
    ?role=Engineer
    ?search=alice                 cross-field search (full_name, email, role)
    ?ordering=full_name
"""
import django_filters
from apps.crm.models import Company, Contact


class CompanyFilter(django_filters.FilterSet):
    """
    Filterable fields for Company list endpoint.

    All fields default to exact match unless overridden.
    icontains lookups are useful for partial/case-insensitive text matching.
    """

    # Exact match (used by dropdowns, faceted filters)
    industry = django_filters.CharFilter(
        field_name="industry",
        lookup_expr="iexact",
        label="Filter by industry (case-insensitive exact match)",
    )
    country = django_filters.CharFilter(
        field_name="country",
        lookup_expr="iexact",
        label="Filter by country (case-insensitive exact match)",
    )

    # Date range filters for created_at
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Filter companies created on or after this datetime (ISO 8601)",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Filter companies created on or before this datetime (ISO 8601)",
    )

    class Meta:
        model = Company
        fields = ["industry", "country", "created_after", "created_before"]


class ContactFilter(django_filters.FilterSet):
    """
    Filterable fields for Contact list endpoint.
    """

    # Filter all contacts for a specific company (UUID FK)
    company = django_filters.UUIDFilter(
        field_name="company__id",
        label="Filter contacts belonging to a specific company (UUID)",
    )

    # Role exact match (case-insensitive)
    role = django_filters.CharFilter(
        field_name="role",
        lookup_expr="iexact",
        label="Filter by job role (case-insensitive exact match)",
    )

    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Filter contacts created on or after this datetime (ISO 8601)",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Filter contacts created on or before this datetime (ISO 8601)",
    )

    class Meta:
        model = Contact
        fields = ["company", "role", "created_after", "created_before"]
