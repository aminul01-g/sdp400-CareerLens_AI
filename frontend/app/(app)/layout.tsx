/**
 * Guarded application shell.
 *
 * A **server** component: the real session check happens here, by calling the API
 * with the request's cookies forwarded. `src/middleware.ts` only checks token
 * presence (the Edge runtime cannot read `localStorage`), so this is the check that
 * actually decides whether to render.
 *
 * A cookie without a valid session produces a redirect rather than a broken shell.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { SkipLink } from "@/components/shared/SkipLink";
import { Footer } from "@/components/layout/Footer";
import { API_BASE_URL, TOKEN_COOKIE } from "@/lib/api/config";

async function hasValidSession(): Promise<boolean> {
  const token = (await cookies()).get(TOKEN_COOKIE)?.value;
  if (!token) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    // The API being unreachable must not render an authenticated shell that will
    // fail every subsequent request; treat it as signed out and let the client
    // surface the connection error.
    return false;
  }
}

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  if (!(await hasValidSession())) redirect("/login");

  return (
    <div className="flex min-h-screen flex-col">
      <SkipLink />
      <Header />
      <main id="main-content" tabIndex={-1} className="container mx-auto flex-1 px-4 py-8">
        {children}
      </main>
      <Footer />
    </div>
  );
}
