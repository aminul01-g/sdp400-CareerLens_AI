/**
 * The machine accessibility check.
 *
 * `docs/accessibility-audit.md` used to say, under "What was not verified":
 *
 *     - **No machine contrast check.** No tool (axe, Lighthouse, Pa11y) was run
 *       against a rendered page. The design system's colour tokens were written by
 *       eye. The `--muted-foreground` on `--background` pair is the one most likely
 *       to fall short of 4.5:1, because it is used for secondary text.
 *
 * This file is that check. `axe-core` computes the contrast ratio of every
 * text/background pair it can resolve on a rendered page, so a palette that
 * was written by eye is now measured.
 *
 * The rules that run are the WCAG 2.2 A and AA rules, tagged
 * `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` and `wcag22aa`. A violation
 * fails the test and names the rule and the element, so a failure is
 * actionable rather than a number.
 *
 * What this does *not* do: it does not read the page the way a screen reader
 * does, and it does not judge whether the reading order makes sense. Those
 * remain unverified, and the limitations document continues to say so.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import {
  ADMIN,
  ADMIN_ROUTES,
  APP_ROUTES,
  PUBLIC_ROUTES,
  adminShellAvailable,
  signIn,
} from "./helpers";

/** The tags axe uses for the WCAG 2.2 A and AA success criteria. */
const WCAG_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function analyse(
  page: import("@playwright/test").Page,
  url: string,
  colorScheme: "light" | "dark" = "light",
) {
  await page.emulateMedia({ colorScheme });
  await page.goto(url);
  // Wait for the page to settle before measuring it.
  //
  // These pages are client components inside a server-rendered shell, so the
  // markup axe would measure straight after `networkidle` is the *server*
  // markup, before hydration has filled in the values that the widgets
  // display. A combobox whose value has not been rendered yet is a button with
  // no accessible name, and axe is right to complain about it — but the user
  // never sees that state. The wait is for the page to stop changing, which
  // is what "the page has loaded" means for a user.
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForFunction(
    () =>
      new Promise<boolean>((resolve) => {
        let last = document.body.innerHTML.length;
        const tick = () => {
          const now = document.body.innerHTML.length;
          if (now === last) {
            resolve(true);
            return;
          }
          last = now;
          setTimeout(tick, 120);
        };
        setTimeout(tick, 120);
      }),
    undefined,
    { timeout: 15_000 },
  );
  return new AxeBuilder({ page }).withTags(WCAG_AA_TAGS).analyze();
}

type AxeViolation = {
  id: string;
  impact?: string | null;
  nodes: { target: unknown }[];
};

function describe(violations: readonly AxeViolation[]) {
  return violations
    .map((violation) => {
      const nodes = violation.nodes
        .map((node) => JSON.stringify(node.target))
        .slice(0, 4)
        .join("\n      ");
      return `${violation.id} (${violation.impact ?? "unknown"}): ${violation.nodes.length} node(s)\n      ${nodes}`;
    })
    .join("\n");
}

test.describe("the public pages", () => {
  // An anonymous browser, for the same reason the administrator block uses
  // one: `/login` and `/register` redirect a signed-in visitor to the
  // dashboard. Measuring them with the shared session was therefore
  // measuring the dashboard, twice, and the two pages themselves were never
  // checked at all.
  test.use({ storageState: { cookies: [], origins: [] } });

  for (const route of PUBLIC_ROUTES) {
    test(`no WCAG A/AA violations on ${route}`, async ({ page }) => {
      const results = await analyse(page, route);
      expect(describe(results.violations), route).toBe("");
    });
  }
});

test.describe("signed in", () => {
  // The session comes from the storage state the setup project wrote; see
  // `e2e/auth.setup.ts`.
  for (const route of APP_ROUTES) {
    test(`no WCAG A/AA violations on ${route}`, async ({ page }) => {
      const results = await analyse(page, route);
      expect(describe(results.violations)).toBe("");
    });
  }
});

test.describe("administrator", () => {
  // Signing in as somebody else needs an anonymous browser: the shared
  // storage state would already be signed in as the demo user, and /login
  // redirects a signed-in visitor away.
  test.use({ storageState: { cookies: [], origins: [] } });

  test("no WCAG A/AA violations on the admin pages", async ({ page }) => {
    test.skip(!adminShellAvailable(), "no administrator credentials were supplied");

    await signIn(page, ADMIN);
    for (const route of ADMIN_ROUTES) {
      const results = await analyse(page, route);
      expect(describe(results.violations), route).toBe("");
    }
  });
});

/**
 * The dark theme.
 *
 * A palette that passes in the light theme can fail in the dark one, because
 * a colour that is dark enough to carry white text is unreadable on a
 * near-black background. The destructive colour is exactly that case: it
 * needed two tokens, a light red for text and a dark red for surfaces, and
 * the only way to know the split is right is to measure both themes.
 */
test.describe("the dark theme", () => {
  test.describe("the public pages", () => {
    // Anonymous, for the same reason the light-theme block is: a signed-in
    // visitor is redirected away from /login and /register.
    test.use({ storageState: { cookies: [], origins: [] } });

    test("no WCAG A/AA violations on the public pages", async ({ page }) => {
      for (const route of ["/", "/login", "/register", "/feedback"]) {
        const results = await analyse(page, route, "dark");
        expect(describe(results.violations), route).toBe("");
      }
    });
  });

  test("no WCAG A/AA violations on the signed-in pages", async ({ page }) => {
    for (const route of ["/dashboard", "/skills", "/profile", "/recommendations"]) {
      const results = await analyse(page, route, "dark");
      expect(describe(results.violations), route).toBe("");
    }
  });
});
