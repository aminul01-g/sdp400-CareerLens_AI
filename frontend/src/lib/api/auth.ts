import { apiFetch } from "./client";
import type { TokenResponse, User } from "./types";

export const authApi = {
  register: (body: { name: string; email: string; password: string; education_level?: string | null }) =>
    apiFetch.post<TokenResponse>("/auth/register", body),
  login: (body: { email: string; password: string }) =>
    apiFetch.post<TokenResponse>("/auth/login", body),
  /** The server holds nothing to revoke; the client discards the token. */
  logout: () => apiFetch.post<void>("/auth/logout"),
  refresh: () => apiFetch.post<TokenResponse>("/auth/refresh", {}),
  me: () => apiFetch.get<User>("/auth/me"),
  updateMe: (body: { name?: string; password?: string; current_password?: string }) =>
    apiFetch.patch<User>("/auth/me", body),
  deleteMe: () => apiFetch.delete<void>("/auth/me"),
};
