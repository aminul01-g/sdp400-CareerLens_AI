/**
 * The AI workspace, in a browser.
 *
 * The CI run has no model provider configured, so these tests cover the state
 * that is *true* on such a deployment: the screens render, they explain
 * honestly that the AI layer is not available, and they point at the features
 * that still work. A test that required a live model would either need a
 * secret in CI or would have to assert nothing.
 *
 * The "not enabled" panel is a real state and worth covering, because the
 * alternative — a button that always fails — is what a careless
 * implementation would have shipped.
 */
import { expect, test } from "@playwright/test";
import { waitForPageReady } from "./helpers";

const AI_ROUTES = [
  { path: "/mentor", heading: /career mentor/i },
  { path: "/roadmaps", heading: /learning roadmap/i },
  { path: "/job-analysis", heading: /job analysis/i },
  { path: "/interview", heading: /mock interview/i },
  { path: "/resume/advice", heading: /cv advice/i },
];

test.describe("the AI workspace", () => {
  test("every AI screen renders and says so honestly when it is unavailable", async ({
    page,
  }) => {
    for (const route of AI_ROUTES) {
      const response = await page.goto(route.path);
      expect(response?.status(), `${route.path} did not return 200`).toBeLessThan(400);
      await waitForPageReady(page);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(route.heading);

      // The shared sub-navigation is on every AI screen.
      await expect(page.getByRole("navigation", { name: "AI tools" })).toBeVisible();

      // And the panel explains the state rather than pretending to work.
      const panel = page.getByText(/not enabled on this deployment/i).first();
      await expect(panel).toBeVisible();

      // The panel points at the features that still work.
      await expect(page.getByRole("link", { name: /get recommendations/i })).toBeVisible();
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

  test("the mentor shows no conversation when the AI layer is unavailable", async ({
    page,
  }) => {
    await page.goto("/mentor");
    await waitForPageReady(page);

    // There is no conversation, because there is nothing to have one with.
    // A chat window with a placeholder "assistant" message in it would be a
    // fabricated answer, and a user would have no way of telling.
    await expect(page.getByRole("log", { name: /conversation/i })).toHaveCount(0);

    // And the reason is stated rather than left to be discovered.
    await expect(
      page.getByText(/not enabled on this deployment/i).first(),
    ).toBeVisible();
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
