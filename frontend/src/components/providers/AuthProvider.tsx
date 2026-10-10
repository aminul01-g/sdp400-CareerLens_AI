"use client";

/**
 * Authentication state.
 *
 * A context wrapping a single `GET /api/auth/me` call — not a state library.
 * On mount it revalidates any stored token, so a session that was revoked or
 * expired server-side is discovered and cleared rather than leaving the UI in a
 * half-authenticated state.
 */
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/config";
import {
  clearSession,
  getStoredUser,
  getToken,
  setSession,
  type SessionUser,
} from "@/lib/auth/session";

interface AuthContextValue {
  user: SessionUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    name: string;
    email: string;
    password: string;
    education_level?: string | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = React.useState<SessionUser | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const revalidate = React.useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
      setSession(getToken() as string, me);
    } catch (error) {
      // A 401 means the token is gone or expired: clear it so the guards stop
      // treating the visitor as signed in. Any other failure keeps the cached
      // user, because a transient network error is not a revoked session.
      if (error instanceof ApiError && error.isUnauthorized) {
        clearSession();
        setUser(null);
      } else {
        setUser(getStoredUser());
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void revalidate();
  }, [revalidate]);

  const login = React.useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login({ email, password });
      setSession(response.access_token, response.user);
      setUser(response.user);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const register = React.useCallback(
    async (input: { name: string; email: string; password: string; education_level?: string | null }) => {
      const response = await authApi.register(input);
      setSession(response.access_token, response.user);
      setUser(response.user);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const logout = React.useCallback(async () => {
    try {
      // Best effort: the token is stateless, so a failure here must not prevent
      // the client from discarding it.
      await authApi.logout();
    } catch {
      /* ignore */
    }
    clearSession();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      // Derived from state only, never from `getToken()`. `getToken` reads
      // localStorage, so it returns null on the server but a value on the
      // client's first render: the server HTML said "signed out" while
      // hydration said "signed in", React threw away the server markup and
      // re-rendered the whole tree on the client. Every consumer then had to
      // cope with a signed-in UI appearing out of nowhere.
      //
      // `revalidate` above runs on mount and sets `user` from the stored token,
      // so the correct value still arrives one tick later. Callers that must not
      // flash the signed-out state branch on `isLoading` first.
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === "admin",
      login,
      register,
      logout,
      refreshUser: revalidate,
    }),
    [user, isLoading, login, register, logout, revalidate],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
