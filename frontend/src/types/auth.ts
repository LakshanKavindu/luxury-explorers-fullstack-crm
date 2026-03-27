/**
 * TypeScript types for all auth-related data.
 * These mirror the Django serializer output shapes exactly.
 */

// ── Role / Plan enums ─────────────────────────────────────────────────────────

export type UserRole = "admin" | "manager" | "staff";
export type OrgPlan  = "basic" | "pro";

// ── API shapes ────────────────────────────────────────────────────────────────

export interface OrganizationInfo {
  id:   string;
  name: string;
  plan: OrgPlan;
}

export interface UserProfile {
  id:           string;
  email:        string;
  full_name:    string;
  role:         UserRole;
  organization: OrganizationInfo;
  date_joined:  string;  // ISO 8601
}

// ── Request / Response shapes ─────────────────────────────────────────────────

export interface LoginRequest {
  email:    string;
  password: string;
}

/** Shape returned by POST /api/v1/auth/token/ */
export interface LoginResponse {
  access:  string;
  refresh: string;
  user:    UserProfile;
}

// ── Auth store state ──────────────────────────────────────────────────────────

export interface AuthState {
  user:         UserProfile | null;
  accessToken:  string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
}
