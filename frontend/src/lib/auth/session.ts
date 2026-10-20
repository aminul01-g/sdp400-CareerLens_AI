/**
 * Session storage for the JWT and the cached user.
 *
 * The keys are new rather than the predecessor's bare `token` / `user`: namespacing
 * them means a stale value from the old Vite app on the same origin can never be
 * read as a valid session. The *behaviour* is deliberately unchanged — the token
 * lives in `localStorage`, which is what the existing UX already did.
 *
 * Known trade-off, recorded rather than hidden: `localStorage` is readable by any
 * XSS payload. The stronger pattern is an httpOnly cookie. Proposal section 7.5
 * asks for "token-based sessions", which this is, so the plan keeps the existing
 * behaviour and documents the limitation. See docs/report.md.
 */
import { TOKEN_COOKIE, TOKEN_KEY, USER_COOKIE, USER_KEY } from "../api/config";
import type { UserRole } from "../api/types";

export interface SessionUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string | null;
}

const isBrowser = typeof window !== "undefined";

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/**
 * Mirror a value into a cookie readable by `middleware.ts`.
 *
 * The API client reads the token from `localStorage` (preserving the existing UX),
 * but Edge middleware **cannot** read `localStorage` — it only has access to
 * cookies. Without this mirror, the route guards in `src/middleware.ts` would be
 * dead code that silently allowed every anonymous visitor straight into
 * `/dashboard`, which is the exact defect the guards exist to fix.
 *
 * The cookie is deliberately not `httpOnly`: the browser bundle never needs to
 * read it, but a non-`httpOnly` cookie is what allows the Edge runtime to see it.
 * The *authoritative* session check is still the server-side one in
 * `app/(app)/layout.tsx` and `require_role("admin")` on the API, neither of which
 * this cookie can influence. See docs/report.md.
 */
function writeCookie(name: string, value: string): void {
  if (!isBrowser) return;
  // The `Secure` attribute is set when — and only when — the page was served
  // over HTTPS. Marking a cookie `Secure` on a plain-HTTP origin makes the
  // browser reject it outright, and the consequence is that a production build
  // served over HTTP (`npm run start`, or a self-hosted deployment without a
  // terminating proxy) cannot store a session at all: the Edge guard reads no
  // cookie and bounces every protected page back to `/login`. The browser
  // suite caught it. The condition is the protocol the page is actually on,
  // not the build mode, because the build mode does not know how the page
  // reaches the browser.
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${ONE_YEAR_SECONDS}; SameSite=Lax${secure}`;
}

function clearCookie(name: string): void {
  if (!isBrowser) return;
  document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`;
}

export function getToken(): string | null {
  if (!isBrowser) return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): SessionUser | null {
  if (!isBrowser) return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: SessionUser): void {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* storage unavailable (private mode); the session simply will not persist */
  }
  // Dual-write so the Edge route guards can see the session. See writeCookie.
  writeCookie(TOKEN_COOKIE, token);
  writeCookie(USER_COOKIE, JSON.stringify(user));
}

export function clearSession(): void {
  if (!isBrowser) return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    /* nothing to do */
  }
  clearCookie(TOKEN_COOKIE);
  clearCookie(USER_COOKIE);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

/**
 * A one-shot message for the sign-in page.
 *
 * Used when a session ends for a reason the user should know about — a
 * password change elsewhere, for instance — so the sign-in page can say why
 * rather than leaving the user wondering why they were signed out.
 */
const NOTICE_KEY = "careerlens_notice";

export function setSessionNotice(message: string): void {
  if (!isBrowser) return;
  try {
    window.sessionStorage.setItem(NOTICE_KEY, message);
  } catch {
    /* storage unavailable; the notice is a nicety, not a requirement */
  }
}

export function takeSessionNotice(): string | null {
  if (!isBrowser) return null;
  try {
    const value = window.sessionStorage.getItem(NOTICE_KEY);
    window.sessionStorage.removeItem(NOTICE_KEY);
    return value;
  } catch {
    return null;
  }
}

export function isAdmin(): boolean {
  return getStoredUser()?.role === "admin";
}
