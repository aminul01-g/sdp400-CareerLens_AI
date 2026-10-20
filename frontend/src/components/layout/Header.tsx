"use client";

/**
 * Application header.
 *
 * Ported from the predecessor's `Header.tsx`. Three corrections are carried:
 *
 * 1. **`react-router-dom` -> `next/link` + `usePathname` + `useRouter`.**
 * 2. **Every authenticated link resolves to a real route.** The old header linked
 *    to `/profile`, `/admin`, `/admin/analytics` and `/admin/questions`; the last
 *    two never existed in any router. The nav below is the full set of routes this
 *    app actually serves.
 * 3. **`isAdmin` is wired.** The old `App.tsx` passed only `isAuthenticated` and
 *    `userEmail`, so `adminNavLinks` was defined but unreachable.
 *
 * The admin group is a client-side affordance only. The real enforcement is
 * `require_role("admin")` on every `/api/admin/*` route.
 */
import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Brain, ChevronDown, LogOut, Menu, Shield, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/components/providers/AuthProvider";
import { cn } from "@/lib/utils";

/** Authenticated navigation. Every entry is a route that exists. */
const userNavLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/skills", label: "Skills" },
  { href: "/projects", label: "Projects" },
  { href: "/education", label: "Education" },
  { href: "/certifications", label: "Certifications" },
  { href: "/resume", label: "Resume" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/skill-gap", label: "Skill Gap" },
  { href: "/feedback", label: "Feedback" },
] as const;

const adminNavLinks = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/jobs", label: "Job Roles" },
  { href: "/admin/taxonomy", label: "Taxonomy" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/feedback", label: "Feedback" },
  { href: "/admin/audit", label: "Audit log" },
  { href: "/admin/evaluation", label: "Evaluation" },
] as const;

const publicNavLinks = [
  { href: "/features", label: "Features" },
  { href: "/about", label: "About" },
] as const;

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isAdmin, logout, isLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  // Close the mobile menu on navigation; leaving it open hides the page the user
  // just asked for.
  React.useEffect(() => setMobileOpen(false), [pathname]);

  const isActive = (href: string) =>
    href === "/admin" ? pathname === "/admin" : pathname === href || pathname.startsWith(`${href}/`);

  async function handleSignOut() {
    await logout();
    router.push("/login");
  }

  const links = isAuthenticated ? userNavLinks : publicNavLinks;

  // The header shows **one** horizontal nav at a time. Ten user links and six
  // admin links measured 385px of overflow at 1536px and 193px even at 1920px,
  // so rendering both at once cannot be made to fit — not by shrinking type,
  // which would break legibility, and not by truncation, which would hide a
  // destination. Instead the admin section replaces the user nav while you are
  // inside it, and the Admin button plus the avatar menu keep the other set one
  // click away. Below `2xl` neither fits, so the hamburger carries both.
  const inAdminSection = pathname === "/admin" || pathname.startsWith("/admin/");

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between gap-4 px-4">
        <Link href={isAuthenticated ? "/dashboard" : "/"} className="flex items-center gap-2 font-semibold">
          <Brain className="h-6 w-6 text-primary" aria-hidden="true" />
          <span>CareerLens <span className="text-primary">AI</span></span>
        </Link>

        <nav
          className={cn("items-center gap-1", inAdminSection ? "hidden" : "hidden 2xl:flex")}
          aria-label="Main"
        >
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={isActive(link.href) ? "page" : undefined}
              className={cn(
                "whitespace-nowrap rounded-md px-2.5 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                isActive(link.href) && "bg-accent text-accent-foreground",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {isLoading ? (
            <div className="h-9 w-24 animate-pulse rounded-md bg-muted" aria-hidden="true" />
          ) : isAuthenticated && user ? (
            <>
              {isAdmin ? (
                <Button asChild size="sm" variant="outline" className="hidden sm:inline-flex">
                  <Link href="/admin">
                    <Shield className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                    Admin
                  </Link>
                </Button>
              ) : null}

              {isAdmin ? (
                <nav
                  className={cn("items-center gap-1", inAdminSection ? "hidden 2xl:flex" : "hidden")}
                  aria-label="Admin"
                >
                  {adminNavLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      aria-current={isActive(link.href) ? "page" : undefined}
                      className={cn(
                        "whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                        isActive(link.href) && "bg-accent text-accent-foreground",
                      )}
                    >
                      {link.label}
                    </Link>
                  ))}
                </nav>
              ) : null}

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-2"
                    // The name is hidden on small viewports, so the button
                    // would otherwise have no accessible name at all.
                    aria-label={`Account menu for ${user.name}`}
                  >
                    <span className="hidden max-w-32 truncate sm:inline">{user.name}</span>
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {user.name.trim().charAt(0).toUpperCase()}
                    </span>
                    <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <span className="block truncate text-sm font-medium">{user.name}</span>
                    <span className="block truncate text-xs font-normal text-muted-foreground">{user.email}</span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/profile">Profile</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/skills">My skills</Link>
                  </DropdownMenuItem>
                  {isAdmin ? (
                    <DropdownMenuItem asChild>
                      <Link href="/admin">Admin panel</Link>
                    </DropdownMenuItem>
                  ) : null}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => void handleSignOut()} className="text-destructive focus:text-destructive">
                    <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            // Both auth buttons are hidden below `sm`, because at 320 CSS
            // pixels the logo, two buttons and the menu button do not fit and
            // the header overflows sideways. The browser suite measured the
            // overflow; the two links are in the mobile panel below, so
            // nothing is lost. See `frontend/e2e/reflow.spec.ts`.
            <>
              <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
                <Link href="/login">Log in</Link>
              </Button>
              <Button asChild size="sm" className="hidden sm:inline-flex">
                <Link href="/register">Get started</Link>
              </Button>
            </>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="2xl:hidden"
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            onClick={() => setMobileOpen((open) => !open)}
          >
            {mobileOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </Button>
        </div>
      </div>

      {mobileOpen ? (
        <div className="border-t 2xl:hidden">
          <nav className="container mx-auto flex flex-col gap-1 px-4 py-3" aria-label="Mobile">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive(link.href) ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-medium hover:bg-accent",
                  isActive(link.href) && "bg-accent",
                )}
              >
                {link.label}
              </Link>
            ))}
            {!isAuthenticated ? (
              <>
                <p
                  role="heading"
                  aria-level={2}
                  className="px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Account
                </p>
                <Link
                  href="/login"
                  className="rounded-md px-3 py-2 text-sm font-medium hover:bg-accent"
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  className="rounded-md px-3 py-2 text-sm font-medium hover:bg-accent"
                >
                  Get started
                </Link>
              </>
            ) : null}
            {isAdmin ? (
              <>
                <p
                  role="heading"
                  aria-level={2}
                  className="px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Admin
                </p>
                {adminNavLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={isActive(link.href) ? "page" : undefined}
                    className={cn(
                      "rounded-md px-3 py-2 text-sm font-medium hover:bg-accent",
                      isActive(link.href) && "bg-accent",
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
              </>
            ) : null}
          </nav>
        </div>
      ) : null}
    </header>
  );
}

export default Header;
