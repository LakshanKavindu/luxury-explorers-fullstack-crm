# Multi-Tenant CRM System
**Associate Full Stack Engineer - Technical Assessment**

This repository contains a production-ready, multi-tenant Customer Relationship Management (CRM) system. Built with a strict separation of concerns, it features a robust Django REST Framework (DRF) backend and a modern React (TypeScript) frontend.

The project demonstrates enterprise-level software engineering patterns, including strict multi-tenant data isolation, role-based access control (RBAC), secure AWS S3 integration for media storage, and an automated activity audit trail.

---

## 🛠️ Tech Stack

**Backend**
- Python 3.10+ & Django 4+
- Django REST Framework (DRF)
- PostgreSQL (Primary Relational Database)
- SimpleJWT (Token-based Authentication)
- Boto3 & django-storages (AWS Cloud Media Integration)

**Frontend**
- React 18+ & TypeScript
- Vite (Build Tooling)
- Zustand (State Management)
- Axios (Centralized API Networking & Interceptors)
- React Router DOM v6+

**Infrastructure**
- AWS S3 (Bucket storage scoped with IAM policies and Pre-signed URLs)

---

## 🏗️ System Architecture & Features

### Multi-Tenant Data Isolation
Data is logically partitioned by `Organization`. Every user belongs to a specific organization (tenant). Isolation is enforced at the query level using a custom `TenantScopedMixin`. Each API ViewSet intercepts the `get_queryset()` handler, strictly appending `.filter(organization=request.user.organization)` to the base query. This guarantees that user queries—whether for listing resources or attempting to access a specific ID—can never bleed across organizational boundaries.

### Role-Based Access Control (RBAC)
User interactions are guarded via custom DRF `BasePermission` classes (`IsAdminRole`, `IsManagerOrAbove`, `IsStaffOrAbove`).
- **Admin**: Full access. Can perform soft deletes (`DELETE` actions).
- **Manager**: Can view, create, and update records, but cannot delete.
- **Staff**: Can view and create records, but cannot alter historical data.

The React frontend mirrors these constraints by selectively rendering actionable UI components (e.g., hiding "Delete" or "Edit" buttons) based on the current user's role payload.

### CRM Modules & AWS S3 Integration
- **Companies**: Users can create corporate entities containing standard descriptor metadata and a company logo.
- **Contacts**: Nested entities associated with a specific company. Native Django `UniqueConstraints` enforce email uniqueness strictly within the same company scope.
- **AWS S3 Cloud Media**: Implements the `django-storages` specification to stream `multipart/form-data` image uploads directly to S3. To maximize security, the bucket is configured to block all public access. The backend relies on expiring Pre-Signed URLs (`AWS_QUERYSTRING_AUTH=True`) to securely serve media to authenticated clients.

### Activity Audit Trail
An append-only `ActivityLog` model sits behind the service layer, hooking into DRF's `perform_create`, `perform_update`, and `destroy` transaction methods. Any state mutation applied to a Company or Contact emits a tracking log capturing the user, the action type, the object ID, and an explicit timestamp. These logs are accessible via the `/activity-logs` dashboard, which is restricted to Admin users.

---

## 🗄️ Data Model Overview

The backend relies on normalized PostgreSQL tables to represent the CRM hierarchies:
- **Organization**: The primary tenant model managing subscription tiers and isolated workspaces.
- **User**: The actor extending `AbstractUser`. Bound to a single `Organization` and assigned specific roles (Admin/Manager/Staff).
- **Company**: Represents a client organization. Contains normalized columns (industry, country) and holds the S3 logo URL string.
- **Contact**: An individual person nested under a `Company`.
- **ActivityLog**: The ledger entry mapping any changes back to the User and the affected object schema.

---

## 📡 API Overview

The backend exposes a highly structured, versioned REST API under `/api/v1/`. Responses adhere to a uniform structure enforced by a custom global exception handler.

**Authentication:**
- `POST /api/v1/auth/token/` - Obtain JWT access/refresh pair
- `POST /api/v1/auth/token/refresh/` - Renew access token
- `GET /api/v1/auth/me/` - Retrieve authenticated user profile

**Companies:**
- `GET /api/v1/crm/companies/` - List (Supports `?search=`, `?page=`)
- `POST /api/v1/crm/companies/` - Create (Consumes `multipart/form-data`)
- `PATCH /api/v1/crm/companies/:id/` - Partial Update (Manager/Admin)
- `DELETE /api/v1/crm/companies/:id/` - Soft Delete (Admin only)

**Contacts:**
- `GET /api/v1/crm/contacts/?company=:id` - List scoped to a company
- `POST /api/v1/crm/contacts/` - Create
- `PATCH /api/v1/crm/contacts/:id/` - Update
- `DELETE /api/v1/crm/contacts/:id/` - Soft Delete

**Audit:**
- `GET /api/v1/activity-logs/` - Read-only log retrieval for Admins

---

## ♻️ Soft Delete Strategy

To preserve historical integrity and maintain valid foreign key references in the `ActivityLog`, records are never dropped from the database via SQL `DELETE`. Instead, calling the destructive API endpoints safely flips a boolean `is_deleted = True` flag on the instance. The `TenantScopedMixin` natively filters out any records where `is_deleted` is true, keeping the active application views clean while storing the ghost data safely for auditing purposes.

---

## 🔐 Security Considerations

- **JWT Authentication**: Secure, stateless authentication enforcing expiration limits.
- **Backend-Enforced Permissions**: Roles are protected natively at the endpoint view layer; frontend UI hiding is merely cosmetic.
- **Strict Tenant Isolation**: Cross-tenant data leaks are mitigated at the deepest ORM filtering scope available.
- **Environment-based Secrets**: No hardcoded API keys exist inside the committed code.
- **S3 Pre-Signed URLs**: The media bucket is completely private. Only the server can broker expiring link access for clients to view uploaded logos.

---

## 🚀 Quick Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL database running locally

### 1. Backend Setup (Django)
Navigate to the `backend` directory and set up your virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

**Environment Variables**
Duplicate the environment template and provide your database and AWS credentials:
```bash
cp .env.example .env
```
Update `.env` with your PostgreSQL credentials and an AWS IAM User containing S3 `putObject/getObject` permissions. 

**Database Migration & Seeding**
```bash
python manage.py migrate

# 🌟 Recommended: Automatically populate the CRM with demo Organizations, Admins, and 30+ Companies to test pagination natively!
python manage.py seed --clear

# Start Backend Server
python manage.py runserver
```

### 2. Frontend Setup (React)
Open a new terminal and navigate to the `frontend` directory:
```bash
cd frontend
npm install
npm run dev
```

### 3. Demo the App!
Navigate your browser to `http://localhost:5173`. If you utilized the `seed` command above, you can securely log in using the primary Administrator account:

> **Email**: `admin@acme.com`
> **Password**: `password123`

---

## 🎥 Demo Walkthrough

A screen recording accompanies this submission. The demo video actively showcases the end-to-end functionality of the system:
1. **System Overview**: Briefly discussing the architecture patterns and directory structures.
2. **Authentication Flow**: Showcasing the JWT retrieval and secure routing.
3. **CRUD Operations**: Demonstrating pagination, S3 `multipart` logo uploading, and enforcing the DRF Form Validation natively on the React UI.
4. **Activity Logging**: Verifying that backend service layers actively monitor and log the CRUD transactions performed during the demo.