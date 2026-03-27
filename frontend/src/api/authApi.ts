/**
 * Auth API service.
 * All functions return the `.data` envelope from ApiRenderer:
 *   { success: boolean, data: T, message: string }
 *
 * The raw Axios response is unwrapped by the caller via `.data.data`.
 */
import apiClient from "./axios";
import type {
  LoginRequest,
  LoginResponse,
  UserProfile,
} from "../types/auth";

const AUTH_BASE = "/auth";

/**
 * Login with email + password.
 * Returns access token, refresh token, and the full user profile.
 * The frontend auth store should call this and store all three.
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    `${AUTH_BASE}/token/`,
    credentials
  );
  return response.data;
}

/**
 * Refresh the access token using the stored refresh token.
 * Called automatically by the Axios interceptor — rarely needed directly.
 */
export async function refreshToken(refresh: string): Promise<{ access: string; refresh: string }> {
  const response = await apiClient.post<{ access: string; refresh: string }>(
    `${AUTH_BASE}/token/refresh/`,
    { refresh }
  );
  return response.data;
}

/**
 * Server-side logout: blacklists the refresh token.
 * Always call this on logout even if you clear localStorage —
 * it prevents the refresh token being reused if it was stolen.
 */
export async function logout(refresh: string): Promise<void> {
  await apiClient.post(`${AUTH_BASE}/logout/`, { refresh });
}

/**
 * Get the current authenticated user's profile.
 * Used to re-hydrate the auth store on app load if localStorage has a token
 * but you want to confirm it's still valid.
 */
export async function getMe(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>(
    `${AUTH_BASE}/me/`
  );
  return response.data;
}

/**
 * Update the current user's own full_name.
 */
export async function updateMe(fullName: string): Promise<UserProfile> {
  const response = await apiClient.patch<UserProfile>(
    `${AUTH_BASE}/me//`,
    { full_name: fullName }
  );
  return response.data;
}
