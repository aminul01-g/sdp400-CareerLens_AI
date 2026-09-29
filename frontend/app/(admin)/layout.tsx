/**
 * Guarded admin shell.
 *
 * Server component, and stricter than the user shell: the session is validated
 * against the API *and* the role is read from the API response, never from the
 * cookie. A tampered cookie claiming `role: "admin"` gets this far and is then
 * rejected here. The authoritative check is still `require_role("admin")` on every
 * `/api/admin/*` route, which the browser cannot bypass.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { API_BASE_URL, TOKEN_COOKIE } from "@/lib/api/config";
import type { User } from "@/lib/api/types";

async function requireAdmin(): Promise<User> {
  const token = (await cookies()).get(TOKEN_COOKIE)?.value;
  if (!token) redirect("/login");

  let user: User | null = null;
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) redirect("/login");
    user = (await response.json()) as User;
  } catch {
    redirect("/login");
  }
  if (user.role !== "admin") redirect("/dashboard");
  return user;
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  await requireAdmin();

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="container mx-auto flex-1 px-4 py-8">{children}</main>
      <Footer />
    </div>
  );
}
