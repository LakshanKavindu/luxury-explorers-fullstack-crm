# Multi-Tenant CRM — Architecture & Implementation Plan

## Current State

| Area | Status |
|---|---|
| Backend | Only `.env` exists. Django not yet scaffolded. |
| Frontend | Vite + TypeScript boilerplate. **React not installed yet.** `axios`, `react-router-dom`, `zustand` already in `package.json`. |

> [!IMPORTANT]
> The frontend must be migrated from vanilla Vite+TS to a React+Vite+TS project. This is the first frontend task.

---

## 1. Backend Folder Structure

```
backend/
├── config/                        # Django project config (renamed from projectname/)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                # Shared settings
│   │   ├── development.py         # Dev overrides (DEBUG=True, etc.)
│   │   └── production.py          # Prod overrides
│   ├── urls.py                    # Root URL conf → /api/v1/
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── accounts/                  # User + Organization + Auth
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py         # IsAdmin, IsManager, IsStaff
│   │   ├── managers.py            # Custom user manager
│   │   └── admin.py
│   │
│   ├── crm/                       # Company + Contact
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── filters.py             # django-filter FilterSets
│   │   ├── services.py            # Business logic layer
│   │   └── admin.py
│   │
│   └── activity/                  # Activity Log
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── signals.py             # or called from services.py
│
├── common/
│   ├── mixins.py                  # TenantScopedMixin, SoftDeleteMixin
│   ├── pagination.py              # StandardResultsPagination
│   ├── renderers.py               # Consistent JSON response format
│   └── exceptions.py             # Custom exception handler
│
├── manage.py
├── .env
├── .env.example
└── requirements/
    ├── base.txt
    ├── development.txt
    └── production.txt
```

### Key libraries (already in requirements.txt)
- `djangorestframework` — DRF
- `djangorestframework-simplejwt` — JWT auth
- `django-filter` — filtering
- `django-storages` + `boto3` — S3 integration
- `psycopg2-binary` — PostgreSQL
- `django-cors-headers` — CORS

---

## 2. Frontend Folder Structure

```
frontend/
├── index.html                     # Update: root div to id="root"
├── vite.config.ts
├── tsconfig.json
├── .env
├── .env.example
│
└── src/
    ├── main.tsx                   # React entry point
    ├── App.tsx                    # Router + layout wrapper
    │
    ├── api/
    │   ├── axios.ts               # Axios instance + interceptors (token injection, 401 handling)
    │   ├── authApi.ts
    │   ├── companyApi.ts
    │   ├── contactApi.ts
    │   └── activityApi.ts
    │
    ├── store/                     # Zustand stores
    │   ├── authStore.ts           # user, token, login/logout actions
    │   ├── companyStore.ts
    │   └── contactStore.ts
    │
    ├── pages/
    │   ├── LoginPage.tsx
    │   ├── DashboardPage.tsx
    │   ├── CompaniesPage.tsx
    │   ├── CompanyDetailPage.tsx  # Nested contacts
    │   └── ActivityLogPage.tsx
    │
    ├── components/
    │   ├── layout/
    │   │   ├── AppLayout.tsx      # Sidebar + header shell
    │   │   ├── Sidebar.tsx
    │   │   └── Header.tsx
    │   ├── ui/
    │   │   ├── Button.tsx
    │   │   ├── Modal.tsx
    │   │   ├── Table.tsx
    │   │   ├── Pagination.tsx
    │   │   ├── SearchBar.tsx
    │   │   ├── Badge.tsx
    │   │   └── Spinner.tsx
    │   ├── companies/
    │   │   ├── CompanyCard.tsx
    │   │   ├── CompanyForm.tsx
    │   │   └── CompanyFilters.tsx
    │   └── contacts/
    │       ├── ContactRow.tsx
    │       └── ContactForm.tsx
    │
    ├── hooks/
    │   ├── useAuth.ts
    │   ├── useCompanies.ts
    │   └── useContacts.ts
    │
    ├── routes/
    │   └── ProtectedRoute.tsx     # Redirects to /login if unauthenticated
    │
    ├── types/
    │   ├── auth.ts
    │   ├── company.ts
    │   ├── contact.ts
    │   └── activity.ts
    │
    └── utils/
        ├── formatDate.ts
        └── errorHandler.ts
```

---

## 3. App / Module Split

| Django App | Responsibility |
|---|---|
| `accounts` | Organization model, Custom User model (email login), JWT auth endpoints, role definitions |
| `crm` | Company + Contact CRUD, S3 logo upload, soft delete, search/filter/pagination |
| `activity` | ActivityLog model, log creation logic (called from `crm/services.py`) |
| `common` | Shared mixins, pagination, response renderer, exception handler |

---

## 4. Step-by-Step Implementation Order

### Phase 1 — Backend Foundation
1. Scaffold Django project: `django-admin startproject config .` inside `backend/`
2. Split settings into `base.py` / `development.py` / `production.py`
3. Configure PostgreSQL in `base.py` using env vars
4. Create `apps/accounts/` — Organization model, Custom User model with role field
5. Run initial migrations
6. Configure `djangorestframework-simplejwt` — `/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`
7. Build custom permission classes: `IsAdminRole`, `IsManagerOrAbove`, `IsStaffOrAbove`
8. Build `TenantScopedMixin` in `common/mixins.py`

### Phase 2 — CRM Module
9. Create `apps/crm/` — Company model with S3 logo field
10. Configure `django-storages` + `boto3` for S3 (signed URLs strategy)
11. Create Contact model with validation
12. Build `CompanyViewSet` and `ContactViewSet` with tenant scoping + soft delete
13. Add `django-filter` FilterSets for search / filtering
14. Add `StandardResultsPagination`
15. Build service layer in `crm/services.py` for business logic

### Phase 3 — Activity Log
16. Create `apps/activity/` — ActivityLog model
17. Call `ActivityLog.objects.create(...)` from inside `crm/services.py` on every C/U/D
18. Build read-only `ActivityLogViewSet` scoped to tenant

### Phase 4 — API Polish
19. Implement `common/renderers.py` — uniform `{ success, data, message, errors }` envelope
20. Implement `common/exceptions.py` — DRF custom exception handler
21. Wire all URLs under `/api/v1/`
22. Set up CORS in settings

### Phase 5 — Frontend Setup
23. Install React dependencies: `react`, `react-dom`, `@types/react`, `@types/react-dom`
24. Update `tsconfig.json` for JSX, rename `main.ts` → `main.tsx`
25. Update `index.html` root div id to `"root"`
26. Build Axios instance with JWT interceptor + refresh logic
27. Build Zustand `authStore` with login/logout/persist
28. Build `ProtectedRoute` wrapper
29. Build `AppLayout` (sidebar + header)

### Phase 6 — Frontend Pages
30. `LoginPage` — form, error handling, redirect on success
31. `DashboardPage` — org name, stats cards
32. `CompaniesPage` — table with search, filter, pagination, logo upload
33. `CompanyDetailPage` — company info + nested contacts table, CRUD modals
34. `ActivityLogPage` — read-only paginated log

### Phase 7 — Production Readiness
35. Add `.env.example` for both backend and frontend
36. Final CORS audit
37. Seed script for demo org/users (for the screen recording)

---

## 5. Data Model Plan

### Organization
```
Organization
├── id              UUID (PK)
├── name            CharField(max_length=255)
├── plan            CharField(choices=['basic', 'pro'], default='basic')
└── created_at      DateTimeField(auto_now_add=True)
```

### User (extends AbstractBaseUser)
```
User
├── id              UUID (PK)
├── organization    ForeignKey(Organization, on_delete=CASCADE)
├── email           EmailField(unique=True)  ← login identifier
├── full_name       CharField
├── role            CharField(choices=['admin', 'manager', 'staff'])
├── is_active       BooleanField(default=True)
├── is_staff        BooleanField(default=False)  ← Django admin access
└── date_joined     DateTimeField(auto_now_add=True)
```

### Company
```
Company
├── id              UUID (PK)
├── organization    ForeignKey(Organization, on_delete=CASCADE)  ← tenant key
├── name            CharField
├── industry        CharField
├── country         CharField
├── logo            ImageField (stored via django-storages → S3)
├── is_deleted      BooleanField(default=False)  ← soft delete
└── created_at      DateTimeField(auto_now_add=True)
```

### Contact
```
Contact
├── id              UUID (PK)
├── company         ForeignKey(Company, on_delete=CASCADE)
├── organization    ForeignKey(Organization, on_delete=CASCADE)  ← tenant key (denormalized for fast filtering)
├── full_name       CharField
├── email           EmailField
├── phone           CharField(optional, 8–15 digits)
├── role            CharField
├── is_deleted      BooleanField(default=False)
└── created_at      DateTimeField(auto_now_add=True)

Constraint: unique_together = [('company', 'email')]
```

### ActivityLog
```
ActivityLog
├── id              UUID (PK)
├── organization    ForeignKey(Organization, on_delete=CASCADE)  ← tenant key
├── user            ForeignKey(User, on_delete=SET_NULL, null=True)
├── action          CharField(choices=['CREATE', 'UPDATE', 'DELETE'])
├── model_name      CharField  (e.g. 'Company', 'Contact')
├── object_id       CharField   (UUID of the affected record)
└── timestamp       DateTimeField(auto_now_add=True)
```

---

## 6. Multi-Tenant Isolation Strategy

### Layer 1 — Database Modeling
Every tenant-owned model (`Company`, `Contact`, `ActivityLog`) has an `organization` ForeignKey. This is the ground truth — no record can exist without an owner.

### Layer 2 — Custom Manager
```python
# common/managers.py
class TenantManager(models.Manager):
    def for_org(self, organization):
        return self.get_queryset().filter(organization=organization)
```
All ViewSets call `.for_org(request.user.organization)` — never the raw `.all()`.

### Layer 3 — TenantScopedMixin (ViewSet level)
```python
# common/mixins.py
class TenantScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(
            organization=self.request.user.organization,
            is_deleted=False
        )

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
```
This mixin is applied to **every** CRM ViewSet. No ViewSet ever constructs a queryset manually.

### Layer 4 — Serializer Validation
Serializers never accept `organization` as an input field (it's write-only, set by the view). This prevents a user from crafting a payload to assign data to a different org.

### Layer 5 — Object-Level Permission Check
For retrieving a single object, DRF's `get_object()` already applies the filtered queryset, so a user requesting `/api/v1/companies/<id-from-other-org>/` will receive a **404** (not 403) by default — leaking no info about existence.

### Layer 6 — Role-Based Access Control

| Role | List/Read | Create | Update | Delete |
|---|---|---|---|---|
| Staff | ✅ | ✅ | ❌ | ❌ |
| Manager | ✅ | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |

Enforced via custom permission classes in `accounts/permissions.py`, applied per-action in ViewSets.

---

## 7. AWS S3 Logo Strategy

**Chosen approach: Pre-signed URLs (not public bucket)**

- Bucket is **private**
- On upload, file is stored via `django-storages` using IAM credentials from env vars
- On read, a **pre-signed URL** (15-min TTL) is generated and returned in the serializer
- `AWS_QUERYSTRING_AUTH=True` in production (overrides the current `.env` value)

> [!WARNING]
> Your current `.env` has `AWS_QUERYSTRING_AUTH=False` and `AWS_DEFAULT_ACL=public-read`. For production, these should be `True` and `None` (private) respectively. The `.env` values are fine for local development/demo.

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Should the frontend be completely rebuilt from scratch (clean React app replacing the current vanilla TS boilerplate), or do you want to keep the existing Vite config and manually wire React in? **Recommended: full clean scaffold** using `npm create vite@latest . -- --template react-ts`.

> [!IMPORTANT]
> **Q2**: The `requirements.txt` at the root level has the pip packages. Do you want to move these into `backend/requirements/base.txt` as part of the restructure, or keep a single flat `requirements.txt`?

> [!IMPORTANT]
> **Q3**: Do you want a Django **superuser seed script** included for the demo recording (pre-creating 2 orgs, 3 roles, sample companies/contacts)?
