/**
 * Shared helpers for the browser suite.
 *
 * The pages under test are behind a session, so almost every spec needs to be
 * signed in. Signing in through the form is deliberate: it exercises the real
 * path, including the cookie the Edge middleware reads, and it means a spec
 * cannot pass by setting a token that the application would have rejected.
 */
import { expect, type Page } from "@playwright/test";

/** The account the suite signs in as. Seeded by the API's seed scripts. */
export const USER = {
  email: "data.scientist@careerlens.dev",
  password: "Demo#Pass2026",
};

/**
 * The administrator the admin specs sign in as.
 *
 * The password comes from the environment, not from this file. A repository
 * that contains an administrator's password is a repository whose history
 * contains it, and the admin shell does not need to be tested by everybody
 * who clones the project. The spec skips itself when the variable is absent.
 */
export const ADMIN = {
  email: process.env.E2E_ADMIN_EMAIL ?? "admin@careerlens.dev",
  password: process.env.E2E_ADMIN_PASSWORD ?? "",
};

/** Whether the administrator credentials were supplied for this run. */
export function adminCredentialsAvailable(): boolean {
  return ADMIN.password.length > 0;
}

/**
 * Sign in through the login form and wait for the shell to load.
 *
 * The wait is for the dashboard heading rather than for a URL, because the
 * redirect target depends on the role and the shell is what actually proves
 * the session took.
 */
export async function signIn(page: Page, account: { email: string; password: string }) {
  await page.goto("/login");
  // The email field is matched by its label; the password field by its type,
  // because the form also carries a "Show password" button whose accessible
  // name contains the word.
  await page.getByLabel("Email", { exact: true }).fill(account.email);
  await page.locator('input[type="password"]').fill(account.password);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
}

/**
 * Wait for a page to finish loading its data.
 *
 * The pages are client components that fetch their data on mount, so the
 * server-rendered HTML is a loading skeleton and the real content — including
 * the page's heading — only exists after hydration. A test that measures the
 * structure of the page has to wait for that, or it measures the skeleton.
 */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForFunction(
    () => {
      const main = document.querySelector("main");
      if (!main) return false;
      if (main.getAttribute("aria-busy") === "true") return false;
      return main.querySelectorAll("h1").length > 0;
    },
    undefined,
    { timeout: 20_000 },
  );
}

/** The pages the suite walks, in the three shells the application has. */
export const PUBLIC_ROUTES = [
  "/",
  "/about",
  "/features",
  "/feedback",
  "/login",
  "/register",
  "/forgot-password",
];

export const APP_ROUTES = [
  "/dashboard",
  "/profile",
  "/skills",
  "/projects",
  "/education",
  "/certifications",
  "/resume",
  "/recommendations",
  "/skill-gap",
  // The AI workspace. On a deployment with no model provider configured these
  // render an honest "not enabled here" panel, which is a real state and is
  // worth covering.
  "/mentor",
  "/roadmaps",
  "/job-analysis",
  "/interview",
  "/resume/advice",
];

export const ADMIN_ROUTES = [
  "/admin",
  "/admin/users",
  "/admin/jobs",
  "/admin/taxonomy",
  "/admin/feedback",
  "/admin/audit",
  "/admin/evaluation",
];

/**
 * The routes the admin shell is allowed to see.
 *
 * The administrator account is created by ``scripts/seed_admin.py`` from the
 * environment, so it may or may not exist on a given machine. The spec skips
 * rather than fails when it is absent: a missing seed is an environment
 * problem, not an accessibility problem.
 */
export function adminShellAvailable(): boolean {
  return adminCredentialsAvailable();
}
