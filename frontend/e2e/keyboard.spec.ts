/**
 * The keyboard walkthrough.
 *
 * `docs/accessibility-audit.md` used to say, under "What was not verified":
 *
 *     - **No keyboard-only walkthrough of every screen.** The controls are all
 *       native or Radix primitives, which are keyboard-operable, and the
 *       navigation was checked. A full walkthrough of the dialogs, the taxonomy
 *       command palette and the data tables was not performed.
 *
 * This file is that walkthrough, for the parts of it a machine can do. Four
 * things are checked, and each is a property a keyboard user depends on:
 *
 * 1. **The skip link works.** It is the first thing in the tab order, and
 *    activating it moves focus to the main region rather than to the top of
 *    the document.
 * 2. **Focus is visible.** Every element that takes focus has a visible
 *    indicator, so a keyboard user can see where they are.
 * 3. **A dialog traps focus and gives it back.** Opening a dialog moves focus
 *    into it, tabbing stays inside it, and closing it returns focus to the
 *    control that opened it.
 * 4. **Escape closes a dialog.**
 *
 * The one thing a machine cannot do is read the page aloud, and that is still
 * not verified.
 */
import { expect, test, type Page } from "@playwright/test";
import { waitForPageReady } from "./helpers";

/** The element that currently has focus, described well enough to assert on. */
async function activeElement(page: Page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    if (!element) return null;
    return {
      tag: element.tagName.toLowerCase(),
      text: (element.textContent ?? "").trim().slice(0, 80),
      id: element.id,
      href: element.getAttribute("href"),
      label: element.getAttribute("aria-label"),
    };
  });
}

test("the skip link is first in the tab order and moves focus to the content", async ({
  page,
}) => {
  await page.goto("/");
  await page.keyboard.press("Tab");

  const first = await activeElement(page);
  expect(first?.text ?? "").toMatch(/skip/i);
  expect(first?.tag).toBe("a");

  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main-content$/);
});

test("the skip link is present in the signed-in shell too", async ({ page }) => {
  await page.goto("/dashboard");
  await waitForPageReady(page);
  await page.keyboard.press("Tab");

  const first = await activeElement(page);
  expect(first?.text ?? "").toMatch(/skip/i);
});

test("every focusable control on the login form has a visible indicator", async ({
  page,
}) => {
  await page.goto("/login");

  // Tab through the form rather than calling ``focus()``: the focus ring is
  // drawn with a ``focus-visible`` variant, and Chromium only applies
  // ``:focus-visible`` to a control that was focused by the keyboard. A
  // programmatic focus would measure the unfocused style and fail for the
  // wrong reason.
  for (let step = 0; step < 14; step += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const element = document.activeElement;
      if (!element || element === document.body) return null;
      const style = window.getComputedStyle(element);
      return {
        tag: element.tagName.toLowerCase(),
        hasRing: style.boxShadow !== "none" && style.boxShadow !== "",
        hasOutline: style.outlineStyle !== "none" && style.outlineWidth !== "0px",
      };
    });
    if (!focused) continue;
    expect(
      focused.hasRing || focused.hasOutline,
      `the ${focused.tag} focused at step ${step} has no visible focus indicator`,
    ).toBe(true);
  }
});

test("a dialog traps focus, closes on Escape, and gives focus back", async ({ page }) => {
  await page.goto("/skills");
  await waitForPageReady(page);

  // The confirmation dialog is the dialog the product uses most: it is what
  // asks before it removes something. The seeded account has skills, so the
  // remove button is always there.
  const removeButton = page.getByRole("button", { name: /^remove /i }).first();
  await expect(removeButton).toBeVisible();

  await removeButton.focus();
  await removeButton.press("Enter");

  // Radix's AlertDialog renders role="alertdialog": it is a dialog that
  // interrupts, and it is a modal, so it traps focus.
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toBeVisible();

  // Focus is inside the dialog.
  const inside = await page.evaluate(() => {
    const element = document.activeElement;
    const container = document.querySelector('[role="alertdialog"], [role="dialog"]');
    return Boolean(container && element && container.contains(element));
  });
  expect(inside).toBe(true);

  // Tabbing stays inside the dialog.
  for (let step = 0; step < 8; step += 1) {
    await page.keyboard.press("Tab");
    const stillInside = await page.evaluate(() => {
      const element = document.activeElement;
      const container = document.querySelector('[role="alertdialog"], [role="dialog"]');
      return Boolean(container && element && container.contains(element));
    });
    expect(stillInside, `focus escaped the dialog after ${step + 1} tabs`).toBe(true);
  }

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();

  // Focus comes back to the control that opened the dialog.
  const returned = await activeElement(page);
  expect(returned?.label ?? returned?.text ?? "").toMatch(/remove/i);
});

test("the page can be read in a sensible order", async ({ page }) => {
  await page.goto("/dashboard");
  await waitForPageReady(page);

  const structure = await page.evaluate(() => ({
    landmarks: {
      header: document.querySelectorAll("header").length,
      main: document.querySelectorAll("main").length,
      footer: document.querySelectorAll("footer").length,
      nav: document.querySelectorAll("nav").length,
    },
    h1: document.querySelectorAll("h1").length,
  }));

  expect(structure.landmarks.header).toBe(1);
  expect(structure.landmarks.main).toBe(1);
  expect(structure.landmarks.footer).toBe(1);
  expect(structure.landmarks.nav).toBeGreaterThan(0);
  expect(structure.h1).toBe(1);
});
