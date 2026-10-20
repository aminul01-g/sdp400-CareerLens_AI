import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

/**
 * The browser test suite.
 *
 * `docs/limitations.md` used to say, of accessibility:
 *
 *     **Accessibility is unaudited against a real audit.** The static structure
 *     is linted and the manual review is written down, but there has been no
 *     screen-reader pass, no machine contrast check, no keyboard walkthrough of
 *     every dialog, and no reflow test.
 *
 * Four of the five gaps in that sentence are closable with a browser, and this
 * is the browser. `axe-core` covers the machine contrast check, because it
 * computes the contrast ratio of every text/background pair it can see rather
 * than trusting a palette. The keyboard walkthrough, the reflow test and the
 * journey are ordinary Playwright tests.
 *
 * What is *not* here, and still not done, is the screen-reader pass. That
 * needs somebody who uses one, and no tool substitutes for that. The
 * limitations document says so in those words.
 *
 * The suite needs the API running, because the pages under test are behind a
 * session and the journey is a real journey. The API is expected on
 * `NEXT_PUBLIC_API_URL` (http://localhost:8000 by default); see
 * `docs/deployment.md` for how to start it.
 */
const BASE_URL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000";

/** The session file the setup project writes and the specs read. */
const AUTH_FILE = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "e2e",
  ".auth",
  "user.json",
);

export default defineConfig({
  testDir: "./e2e",
  // The suite drives a real application against a real API, so the specs
  // share state through the database. Running them in parallel would make a
  // failure depend on which worker got there first.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      // Sign in once, and let the other projects reuse the session. Signing
      // in per spec would spend the deployment's authentication rate limit,
      // which is a *global* limit now that the counters live in the database.
      name: "setup",
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: "chromium",
      dependencies: ["setup"],
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_FILE,
      },
    },
  ],
  webServer: {
    // The production server rather than the dev server: the dev server
    // recompiles on the fly, which makes a timing-sensitive test flaky and
    // tests something nobody deploys.
    command: "npm run start",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    },
  },
});
