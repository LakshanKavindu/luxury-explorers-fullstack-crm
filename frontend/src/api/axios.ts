/**
 * Axios instance with JWT authentication interceptors.
 *
 * Two interceptors are registered:
 *
 * 1. REQUEST interceptor
 *    Reads the access token from Zustand's authStore and injects it
 *    as `Authorization: Bearer <token>` on every outgoing request.
 *    The login endpoint is intentionally not excluded — the server ignores
 *    the header on public endpoints.
 *
 * 2. RESPONSE interceptor (401 handler)
 *    When a 401 is received, it means the access token has expired.
 *    The interceptor:
 *      a. Pauses all inflight requests (using a queue and an isRefreshing flag).
 *      b. Sends one /token/refresh/ call with the stored refresh token.
 *      c. On success: stores the new tokens, retries the original request.
 *      d. On failure (refresh also expired): clears auth state → forces login.
 *
 * Token storage strategy:
 *    Tokens are stored in Zustand's authStore which persists to localStorage
 *    via the `persist` middleware. This is the standard SPA approach and is
 *    acceptable for this assessment. In a high-security context, the access
 *    token would be kept in memory (JS variable) and the refresh token in
 *    an HttpOnly cookie to mitigate XSS.
 *
 * Usage:
 *    All API files import `apiClient` from this module — never create a new
 *    Axios instance elsewhere. This ensures every request goes through the
 *    interceptors.
 */
import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "../store/authStore";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Refresh queue ─────────────────────────────────────────────────────────────
// When multiple requests fail with 401 simultaneously, only one refresh call
// is sent. The others are queued and resolved/rejected when refresh completes.

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token!);
    }
  });
  failedQueue = [];
}

// ── Request interceptor ───────────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const accessToken: string | null = useAuthStore.getState().accessToken;

    if (accessToken && config.headers) {
      config.headers["Authorization"] = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// ── Response interceptor (401 → auto-refresh) ─────────────────────────────────

apiClient.interceptors.response.use(
  (response) => {
    // If it's our standard backend envelope, unwrap it.
    // This ensures apiClient.get(...).then(res => res.data) points to the actual payload.
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return {
        ...response,
        data: response.data.data
      };
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    const isUnauthorized = error.response?.status === 401;
    const isRefreshEndpoint = originalRequest.url?.includes("/auth/token/refresh");
    const alreadyRetried = originalRequest._retry === true;

    // Don't attempt refresh for the refresh endpoint itself, or if already retried
    if (!isUnauthorized || isRefreshEndpoint || alreadyRetried) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Another request is already refreshing — queue this one
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers = {
            ...(originalRequest.headers ?? {}),
            Authorization: `Bearer ${token}`,
          };
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken: string | null = useAuthStore.getState().refreshToken;

    if (!refreshToken) {
      // No refresh token stored — force logout
      useAuthStore.getState().logout();
      isRefreshing = false;
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      });

      const newAccessToken: string = data.data.access;
      const newRefreshToken: string = data.data.refresh;

      // Update the store with new tokens
      useAuthStore.setState({
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      });

      // Update the header on the original request and retry
      originalRequest.headers = {
        ...(originalRequest.headers ?? {}),
        Authorization: `Bearer ${newAccessToken}`,
      };

      processQueue(null, newAccessToken);
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      // Refresh failed → force logout and redirect to login
      useAuthStore.getState().logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default apiClient;
