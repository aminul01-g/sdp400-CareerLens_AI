/**
 * Signing in, once.
 *
 * The suite signs in as the demo user in several files, and the rate limiter
 * counts every sign-in against one client address — the deployment-wide limit
 * that `app/core/rate_limit.py` now enforces. Signing in once and reusing the
 * session is both faster and the only thing that keeps the suite under the
 * limit.
 *
 * The state file is written to a directory that is not committed. It holds a
 * live access token, so it must never be in the repository.
 */
import { test as setup, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { USER } from "./helpers";

export const AUTH_FILE = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  ".auth",
  "user.json",
);

setup("sign in as the demo user", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(USER.email);
  await page.locator('input[type="password"]').fill(USER.password);
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  await page.context().storageState({ path: AUTH_FILE });
});
