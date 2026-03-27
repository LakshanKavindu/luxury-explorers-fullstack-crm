/**
 * CRM Types matching Backend DRF serializers and views.
 */

// ── Generic Pagination Response ──────────────────────────────────────────────
export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── Company ──────────────────────────────────────────────────────────────────
export interface Company {
  id: string;
  name: string;
  industry: string;
  country: string;
  logo_url: string | null;
  is_deleted?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CompanyListFilters {
  search?: string;
  industry?: string;
  country?: string;
  ordering?: string; // "-created_at"
  page?: number;
  page_size?: number;
}

// ── Contact ──────────────────────────────────────────────────────────────────
export interface Contact {
  id: string;
  company?: string; // write (uuid)
  company_detail?: { id: string; name: string }; // read
  full_name: string;
  email: string;
  phone: string;
  role: string;
  is_deleted?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ContactListFilters {
  search?: string;
  company?: string; // scope to a specific company ID
  role?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

// ── Activity Log ─────────────────────────────────────────────────────────────
export interface ActivityLog {
  id: string;
  user_display: string;
  action: number;
  action_display: string; // 'Create', 'Update', 'Delete'
  model_name: string;
  object_id: string;
  object_repr: string;
  timestamp: string;
}

export interface ActivityLogFilters {
  search?: string;
  page?: number;
  page_size?: number;
  ordering?: string; // default "-timestamp"
}

