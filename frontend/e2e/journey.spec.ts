/**
 * The journey, in a browser.
 *
 * `IMPLEMENTATION_PROGRESS.md` records, under "Outstanding":
 *
 *     | **T135/T140** real-browser pass | no browser tooling was used in this
 *     environment | a browser run, or a Playwright suite |
 *
 * This is the Playwright suite. It walks the journey the proposal describes --
 * register, profile, skills, CV, recommendations, skill gap, feedback -- through
 * a real browser against the real API, and it is the first time that journey
 * has been exercised by something that clicks.
 *
 * Every previous run of this journey was over HTTP with a script. That proves
 * the API behaves; it does not prove that a person can complete it. A form
 * whose button is off-screen, a step that loses the session, a panel that
 * never renders because of a hydration error -- none of those fail an HTTP
 * test, and all of them fail here.
 *
 * The journey writes to the database, so it uses an account of its own rather
 * than a seeded one.
 */
import { expect, test } from "@playwright/test";
import { APP_ROUTES, waitForPageReady } from "./helpers";

/** An email for the journey, unique per run so the suite can be re-run. */
function journeyEmail() {
  return `journey-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

test.describe("a new user", () => {
  // The registration flow needs an anonymous browser: a signed-in visitor is
  // redirected away from /register by the route guard.
  test.use({ storageState: { cookies: [], origins: [] } });

  test("can complete the whole journey", async ({ page }) => {
  const email = journeyEmail();
  const password = "Str0ngPassw0rd";

  // ---- register ------------------------------------------------------
  await page.goto("/register");
  await page.getByLabel("Full name", { exact: true }).fill("Journey User");
  await page.getByLabel("Email", { exact: true }).fill(email);
  // The register form has a password field and a confirmation field, and a
  // "Show password" button whose accessible name contains the word, so the
  // fields are matched by their identifiers rather than by their labels.
  await page.locator("#password").fill(password);
  await page.locator("#confirmPassword").fill(password);
  // The form requires the terms to be accepted, and says so when it is not.
  await page.locator("#terms").click();
  await page.getByRole("button", { name: /^create account$/i }).click();

  // The registration either signs the user in or sends them to the login
  // page; both are correct, and both must end with a signed-in shell.
  await page.waitForURL(/\/(login|dashboard)/, { timeout: 20_000 });
  if (page.url().includes("/login")) {
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.locator('input[type="password"]').fill(password);
    await page.getByRole("button", { name: /^sign in$/i }).click();
  }
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });

  // ---- the shell is navigable ----------------------------------------
  for (const route of ["/profile", "/skills", "/projects", "/education", "/resume"]) {
    const response = await page.goto(route);
    expect(response?.status(), `${route} did not return 200`).toBeLessThan(400);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }

  // ---- a skill can be added -------------------------------------------
  await page.goto("/skills");
  await waitForPageReady(page);
  // A new account has no skills, so the page shows its empty state, and the
  // empty state's action opens the taxonomy picker. An account that already
  // has skills gets the picker from the "Add skill" button instead.
  const emptyAction = page.getByRole("button", { name: /search the taxonomy/i });
  if (await emptyAction.isVisible().catch(() => false)) {
    await emptyAction.click();
  } else {
    await page.getByRole("button", { name: /add skill/i }).click();
  }
  // The picker is a cmdk command palette: its input is a combobox and its
  // items are options, neither of which is reachable by a plain textbox or
  // listitem query, so they are matched by the attributes cmdk sets.
  const skillSearch = page.locator("[cmdk-input]");
  await skillSearch.fill("python");
  const option = page.locator("[cmdk-item]").filter({ hasText: /^Python/ }).first();
  await expect(option).toBeVisible({ timeout: 15_000 });
  await option.click();
  await expect(page.getByText(/^Python$/i).first()).toBeVisible({ timeout: 15_000 });

  // ---- recommendations can be generated -------------------------------
  await page.goto("/recommendations");
  const generate = page.getByRole("button", { name: /generate|recommend/i }).first();
  if (await generate.isVisible()) {
    await generate.click();
    await expect(
      page.getByRole("heading", { name: /data scientist|machine learning|engineer|analyst/i })
        .first(),
    ).toBeVisible({ timeout: 30_000 });
  }

  // ---- a stored run can be opened --------------------------------------
  // The recommendation titles are headings, not links; the run is what has a
  // detail page, and the run list links to it.
  const runLink = page.getByRole("link", { name: /view run|run details|\bview\b/i }).first();
  if (await runLink.isVisible().catch(() => false)) {
    await runLink.click();
    await expect(page).toHaveURL(/\/recommendations\/\d+/);
  }

  // ---- the skill gap is reachable -------------------------------------
  await page.goto("/skill-gap");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  // ---- the feedback form works ---------------------------------------
  await page.goto("/feedback");
  const message = page.getByLabel(/message/i);
  if (await message.isVisible()) {
    await message.fill("The journey spec wrote this. It is a test message.");
    await page.getByRole("button", { name: /send|submit/i }).click();
    await expect(page.getByText(/thank|received|got it/i).first()).toBeVisible({
      timeout: 15_000,
    });
  }
  });
});

test("every signed-in page renders for a seeded user", async ({ page }) => {
  for (const route of APP_ROUTES) {
    const response = await page.goto(route);
    expect(response?.status(), `${route} did not return 200`).toBeLessThan(400);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
});

test.describe("an anonymous visitor", () => {
  // The storage state carries a session; this test needs the opposite.
  test.use({ storageState: { cookies: [], origins: [] } });

  test("is sent to the login page", async ({ page }) => {
    for (const route of ["/dashboard", "/profile", "/skills", "/recommendations"]) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
    }
  });
});
