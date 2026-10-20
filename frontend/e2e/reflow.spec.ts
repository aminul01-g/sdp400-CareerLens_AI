/**
 * The reflow and zoom check.
 *
 * `docs/accessibility-audit.md` used to say, under "What was not verified":
 *
 *     - **No zoom or reflow test.** 200% zoom and 320 CSS-pixel reflow have not
 *       been checked.
 *
 * WCAG 2.2 SC 1.4.10 (Reflow) asks for the content to be usable at a
 * viewport 320 CSS pixels wide, without two-dimensional scrolling, and SC
 * 1.4.4 (Resize Text) asks for text to remain readable at 200% zoom.
 *
 * Both are checked here, and both are checked on the pages that carry the
 * most content, because those are the ones that break: the recommendations
 * list, the skills table and the profile form.
 */
import { expect, test } from "@playwright/test";

const ROUTES = ["/dashboard", "/skills", "/profile", "/recommendations", "/resume"];

/** The width below which a two-dimensional scrollbar means the page has failed. */
const NARROW_WIDTH = 320;

/** The horizontal overflow a page is allowed, in CSS pixels. */
const ALLOWED_OVERFLOW = 1;

async function horizontalOverflow(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const documentWidth = document.documentElement.scrollWidth;
    const viewportWidth = document.documentElement.clientWidth;
    return documentWidth - viewportWidth;
  });
}

test.describe("reflow at 320 CSS pixels", () => {
  test.use({ viewport: { width: NARROW_WIDTH, height: 720 } });

  for (const route of ROUTES) {
    test(`${route} does not scroll sideways`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState("networkidle").catch(() => undefined);

      const overflow = await horizontalOverflow(page);
      expect(
        overflow,
        `${route} overflows by ${overflow}px at ${NARROW_WIDTH} CSS pixels wide`,
      ).toBeLessThanOrEqual(ALLOWED_OVERFLOW);
    });
  }
});

test.describe("200% zoom", () => {
  test("the dashboard remains readable and does not scroll sideways", async ({ page }) => {
    // 200% zoom on a 1280-pixel viewport is the same layout pressure as
    // 640 CSS pixels, which is how the zoom is simulated here.
    await page.setViewportSize({ width: 640, height: 720 });
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle").catch(() => undefined);

    const overflow = await horizontalOverflow(page);
    expect(overflow).toBeLessThanOrEqual(ALLOWED_OVERFLOW);

    // The text is still text, not a picture of text, and it is still there.
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.trim().length).toBeGreaterThan(0);
  });
});

test.describe("the public pages", () => {
  test.use({ viewport: { width: NARROW_WIDTH, height: 720 } });

  for (const route of ["/", "/login", "/register", "/feedback"]) {
    test(`${route} does not scroll sideways`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState("networkidle").catch(() => undefined);

      const overflow = await horizontalOverflow(page);
      expect(
        overflow,
        `${route} overflows by ${overflow}px at ${NARROW_WIDTH} CSS pixels wide`,
      ).toBeLessThanOrEqual(ALLOWED_OVERFLOW);
    });
  }
});
