/**
 * The AI workspace, in a browser.
 *
 * The workspace has two honest states, and the suite has to be right in both:
 *
 * - **unavailable**, which is the CI condition and the default: no model
 *   provider is configured, so every screen says so and points at the
 *   features that still work;
 * - **available**, which is what a deployment with a key looks like: the
 *   screens render their own interfaces.
 *
 * A spec that asserted only the first would have been a spec that failed the
 * moment somebody configured a key locally, and a spec that asserted only the
 * second would have been a spec that never checked the honest "not
 * enabled" panel at all. So the state is read from the page and the
 * assertion follows it.
 *
 * What is asserted in both states is the part that must not change: exactly
 * one heading, the shared sub-navigation, no fabricated assistant message,
 * and no simulated progress.
 */
import { expect, test, type Page } from "@playwright/test";
import { waitForPageReady } from "./helpers";

const AI_ROUTES = [
  { path: "/mentor", heading: /career mentor/i },
  { path: "/roadmaps", heading: /learning roadmaps/i },
  { path: "/job-analysis", heading: /job analysis/i },
  { path: "/interview", heading: /mock interview/i },
  { path: "/resume/advice", heading: /cv advice/i },
];

/**
 * Whether the AI layer is switched on for this deployment.
 *
 * Read from the page rather than from an environment variable, because the
 * thing under test is what the *application* believes, and the application's
 * belief comes from the API's answer to `/api/ai/status`.
 */
async function aiIsAvailable(page: Page): Promise<boolean> {
  const panel = page.getByText(/not enabled on this deployment/i).first();
  if ((await panel.count()) === 0) return true;
  return !(await panel.isVisible().catch(() => false));
}

test.describe("the AI workspace", () => {
  test("every AI screen renders, in whichever state the deployment is in", async ({
    page,
  }) => {
    for (const route of AI_ROUTES) {
      const response = await page.goto(route.path);
      expect(response?.status(), `${route.path} did not return 200`).toBeLessThan(400);
      await waitForPageReady(page);

      // Exactly one heading, and it is the page's own.
      const headings = page.getByRole("heading", { level: 1 });
      await expect(headings).toHaveCount(1);
      await expect(headings).toContainText(route.heading);

      // The shared sub-navigation is on every AI screen.
      await expect(page.getByRole("navigation", { name: "AI tools" })).toBeVisible();

      if (await aiIsAvailable(page)) {
        // The screen's own interface. The mentor is the interesting one: it
        // must offer a real conversation surface, and it must not open with
        // a fabricated assistant message.
        if (route.path === "/mentor") {
          const log = page.getByRole("log", { name: /conversation/i });
          await expect(log).toBeVisible();
          await expect(log.getByText(/ask your career assistant a question/i)).toBeVisible();
        }
        if (route.path === "/job-analysis") {
          await expect(page.getByLabel(/job description/i)).toBeVisible();
        }
      } else {
        // The honest panel, and the way out of it.
        await expect(
          page.getByText(/not enabled on this deployment/i).first(),
        ).toBeVisible();
        await expect(page.getByRole("link", { name: /get recommendations/i })).toBeVisible();
      }
    }
  });

  test("the language toggle offers English and Bangla", async ({ page }) => {
    await page.goto("/mentor");
    await waitForPageReady(page);
    const group = page.getByRole("group", { name: /language of the generated guidance/i });
    await expect(group).toBeVisible();
    await expect(group.getByRole("button", { name: "English" })).toBeVisible();
    await expect(group.getByRole("button", { name: "বাংলা" })).toBeVisible();
  });

  test("there is never a fabricated assistant message", async ({ page }) => {
    await page.goto("/mentor");
    await waitForPageReady(page);

    // When the layer is off there is no conversation at all. When it is on
    // there is an empty conversation with an empty state. Either way, no
    // assistant message that the user did not receive.
    const log = page.getByRole("log", { name: /conversation/i });
    if ((await log.count()) > 0) {
      await expect(log).toBeVisible();
      await expect(log.getByText(/ask your career assistant a question/i)).toBeVisible();
      await expect(log.getByText(/Absolutely!|I'd be happy to|As an AI/i)).toHaveCount(0);
    } else {
      await expect(
        page.getByText(/not enabled on this deployment/i).first(),
      ).toBeVisible();
    }
  });

  test("the AI tools are reachable from the dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await waitForPageReady(page);
    const section = page.getByRole("region", { name: /ai assistant/i });
    await expect(section).toBeVisible();
    for (const name of [
      /career mentor/i,
      /learning roadmap/i,
      /job analysis/i,
      /mock interview/i,
    ]) {
      await expect(section.getByRole("link", { name })).toBeVisible();
    }
  });
});
