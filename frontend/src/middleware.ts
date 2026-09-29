import { NextResponse, type NextRequest } from "next/server";

import { TOKEN_COOKIE, USER_COOKIE } from "@/lib/api/config";

/**
 * Route guards.
 *
 * The predecessor app had **no** route guards at all — `App.tsx:75-123` registered
 * ten routes with no `<Navigate>` wrapper, so any visitor could open `/dashboard`
 * and see an authenticated shell. This closes that.
 *
 * Two honest limitations, both consequences of keeping the existing UX:
 *
 * 1. The token is in `localStorage`, which `middleware.ts` (Edge runtime) cannot
 *    read. So this checks for *token presence* and lets the server-side layouts
 *    do the real work: `app/(app)/layout.tsx` and `app/(admin)/layout.tsx` are
 *    React server components that revalidate against the API before rendering.
 *    A guard that only checked presence would be trivially bypassed; a guard that
 *    checked the real session would need a cookie. See docs/report.md.
 * 2. The role check decodes the JWT payload without verifying the signature. It
 *    is a UX affordance that avoids rendering an admin shell to a `user`; the
 *    real enforcement is `require_role("admin")` on every `/api/admin/*` route,
 *    which cannot be bypassed from the browser.
 */

/** Routes that require a session. */
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/profile",
  "/skills",
  "/projects",
  "/education",
  "/certifications",
  "/resume",
  "/recommendations",
  "/skill-gap",
];

/** Routes that require the admin role. */
const ADMIN_PREFIX = "/admin";

/** Pages a signed-in visitor should not be shown again. */
const AUTH_PAGES = ["/login", "/register"];

function hasToken(request: NextRequest): boolean {
  return Boolean(request.cookies.get(TOKEN_COOKIE)?.value ?? null);
}

function isAdminToken(request: NextRequest): boolean {
  const raw = request.cookies.get(USER_COOKIE)?.value;
  if (!raw) return false;
  try {
    const user = JSON.parse(raw) as { role?: string };
    return user.role === "admin";
  } catch {
    return false;
  }
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  const isAdmin = pathname === ADMIN_PREFIX || pathname.startsWith(`${ADMIN_PREFIX}/`);
  const isAuthPage = AUTH_PAGES.includes(pathname);

  const signedIn = hasToken(request);

  if ((isProtected || isAdmin) && !signedIn) {
    // Preserve the attempted path so login can send the user back to it.
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?from=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }

  if (isAdmin && !isAdminToken(request)) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (isAuthPage && signedIn) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Everything except Next internals, the API, and static assets.
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|placeholder.svg|.*\\.(?:png|jpg|jpeg|gif|svg|ico|webp|woff2?)$).*)",
  ],
};
