/**
 * Zustand auth store.
 *
 * Responsibilities:
 *   - Store access token, refresh token, and user profile in memory.
 *   - Persist to localStorage via the `persist` middleware so users
 *     stay logged in after a page refresh.
 *   - Expose login() and logout() actions that the LoginPage calls directly.
 *   - The Axios interceptor reads tokens directly from the store via
 *     useAuthStore.getState() — no React hook required.
 *
 * Storage key: "crm-auth"   (in localStorage)
 *
 * Token storage note:
 *   Storing JWTs in localStorage is acceptable for this assessment.
 *   In a production system with strict XSS requirements, keep the access
 *   token in a JS closure (memory) and the refresh token in an HttpOnly
 *   cookie. The trade-off is that memory storage loses the token on
 *   page refresh, requiring a cookie-based silent refresh flow.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { login as loginApi, logout as logoutApi } from "../api/authApi";
import type { UserProfile, LoginRequest, AuthState } from "../types/auth";

interface AuthActions {
  login:  (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: UserProfile) => void;
  clearAuth: () => void;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  user:            null,
  accessToken:     null,
  refreshToken:    null,
  isAuthenticated: false,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // ── State ──────────────────────────────────────────────────────────────
      ...initialState,

      // ── Actions ────────────────────────────────────────────────────────────

      /**
       * Login: call the API, store tokens and user profile.
       * Throws on invalid credentials (let the LoginPage handle the error).
       */
      login: async (credentials: LoginRequest): Promise<void> => {
        const data = await loginApi(credentials);
        set({
          user:            data.user,
          accessToken:     data.access,
          refreshToken:    data.refresh,
          isAuthenticated: true,
        });
      },

      /**
       * Logout:
       *   1. Blacklist the refresh token on the server.
       *   2. Clear all local auth state regardless of server response.
       *
       * The server call may fail if the token is already blacklisted or
       * the network is down — we clear the state anyway so the user is
       * always logged out locally.
       */
      logout: async (): Promise<void> => {
        const { refreshToken } = get();
        if (refreshToken) {
          try {
            await logoutApi(refreshToken);
          } catch {
            // Silently ignore — local state is cleared regardless
          }
        }
        get().clearAuth();
      },

      /** Update user profile after a PATCH /me call. */
      setUser: (user: UserProfile): void => { set({ user }); },

      /** Hard-clear all auth state (called by Axios interceptor on 401 after failed refresh). */
      clearAuth: (): void => { set(initialState); },
    }),
    {
      name:    "crm-auth",                          // localStorage key
      storage: createJSONStorage(() => localStorage),
      // Only persist tokens and user — not function references
      partialize: (state) => ({
        user:         state.user,
        accessToken:  state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
