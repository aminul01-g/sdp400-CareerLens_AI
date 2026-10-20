# Accessibility Audit

What was checked, how, and what was not.

`docs/limitations.md` used to say accessibility was "untested against a real
audit", that semantic HTML and keyboard paths were used throughout, and that no
screen-reader pass or WCAG conformance check had been performed.

**No formal WCAG conformance statement is made.** See
[What was not verified](#what-was-not-verified) — the reasons are honest, not
procedural.

---

## How it was checked

### 1. Static analysis, enforced in the build gate

`eslint-plugin-jsx-a11y` is in the ESLint rule set for the frontend
(`frontend/eslint.config.js`), and `npm run lint` fails on a violation. This is a
**continuous** check, not a one-off pass: the rule set is part of the same
gate that catches unused variables and broken hooks, so a regression fails the
build rather than waiting for the next audit.

The recommended rule set is enabled, with two rules deliberately turned off and
the reason recorded in the config file:

| Rule | Status | Why |
|---|---|---|
| `jsx-a11y/heading-has-content` | Off for `src/components/ui/**` only | `CardTitle` and `AlertTitle` are heading elements whose content arrives as children from the caller. The rule cannot see it. Editing vendored shadcn/ui code to satisfy a linter would make the next `shadcn add` produce a diff, which is the thing the vendor rule is there to avoid. |
| `jsx-a11y/no-autofocus` | Off | Focus management in a dialog is legitimate. The question the rule cannot ask is *where* focus goes; that is a manual check, listed below. |
| `jsx-a11y/no-noninteractive-element-interactions` | Off | Clickable cards are used as links. This is a design decision, and the card components carry the keyboard handling that makes it work. |

Every other recommended rule is an **error**, not a warning. The frontend
currently passes with zero findings.

### 2. A browser, and what it found

`frontend/e2e/` is a Playwright suite that drives the real application against
the real API. It is run with `npm run test:e2e`. It is not a substitute for a
human audit, and it is not the whole of this one either — it is the part a
machine can do, done properly.

| Spec | What it does | Result |
|---|---|---|
| `a11y.spec.ts` | Runs `axe-core` over every route in both colour schemes, with the WCAG 2.2 A and AA rule sets (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`) | **No violations.** 19 routes, light and dark |
| `keyboard.spec.ts` | Tab order, the skip link, a visible focus indicator on every focusable control, focus trapping in a modal, `Escape` to close, and focus returning to the control that opened the dialog | **Passing.** |
| `reflow.spec.ts` | 320 CSS pixels and 200% zoom, checking that nothing scrolls sideways | **Passing.** |
| `journey.spec.ts` | Register → profile → skills → CV → recommendations → skill gap → feedback, through a real browser | **Passing.** |

The suite found four real defects that no linter could have found. All four are
fixed, and all four have a test that fails if they come back.

#### 2a. The destructive colour failed contrast in both themes

The `--destructive` token was a single colour doing two jobs: it was the fill
of the destructive button *and* the colour of destructive text. White text on
the light theme's red was **3.78:1**, and the dark theme's red was **2.0:1**
as text on a near-black background. Both are below the 4.5:1 that WCAG 1.4.3
requires.

One colour cannot do both jobs in both themes: a red dark enough to carry
white text is unreadable on a near-black background, and a red light enough to
read on a near-black background cannot carry white text. So the token is now
two:

| Token | Light theme | Dark theme | Job |
|---|---|---|---|
| `--destructive` | `0 84% 42%` | `0 84% 66%` | destructive **text** |
| `--destructive-surface` | `0 84% 42%` | `0 62.8% 30.6%` | destructive **surfaces** |
| `--destructive-foreground` | `0 0% 100%` | `210 40% 98%` | the text on a destructive surface |

The measured ratios after the change:

| Pair | Ratio |
|---|---|
| White on `--destructive-surface` (light) | 6.06:1 |
| `--destructive` text on white (light) | 6.06:1 |
| `--destructive` text on `--destructive-surface/15` (light) | 4.65:1 |
| `--destructive-foreground` on `--destructive-surface` (dark) | 9.56:1 |
| `--destructive` text on the dark background | 6.25:1 |

The same audit found `text-amber-600` at 3.19:1 and `text-emerald-600` at
3.77:1 on white. Both were moved one step darker (`amber-700` at 5.02:1,
`emerald-700` at 5.48:1), with their dark-theme counterparts unchanged.

#### 2b. The proficiency sliders had no accessible name

Radix renders the focusable `role="slider"` element on the **Thumb**, and the
name comes from the Thumb's own `aria-label`. Every call site passed
`aria-label` to the Root, where it went nowhere, and with a single value
Radix's own fallback label is `undefined`. Nineteen sliders were unnamed.

`src/components/ui/slider.tsx` now puts the Root's `aria-label` on the Thumb.
The call sites do not change.

#### 2c. Two select triggers had no accessible name

The role-family and role-count filters on the recommendations page, and two
filters on the admin job list, are `role="combobox"` buttons whose name came
only from their selected value. They now carry an `aria-label` as well.

#### 2d. The page scrolled sideways at 320 CSS pixels

Two pages failed WCAG 1.4.10 (Reflow):

* The **header** overflowed by 52 pixels at 320 CSS pixels wide, because the
  logo, two sign-in buttons and the menu button do not fit. The two buttons
  are now hidden below `sm` and both links are in the mobile navigation
  panel, so nothing is lost.
* The **skills page** overflowed by 14 pixels, because a grid item's default
  `min-width: auto` is its min-content width and one wide card was enough to
  make the single column wider than the viewport. The grid items now carry
  `min-w-0`.

### 3. Manual review, by hand

The things a linter cannot judge were read and checked directly:

| Area | What was checked | Result |
|---|---|---|
| Skip link | Present, first in the tab order, invisible until focused, moves focus to the main region | Added (`src/components/shared/SkipLink.tsx`), wired into all three shells |
| Focus indicator | A visible focus ring on every interactive element | **Was missing.** Several shadcn/ui components remove the browser's default ring, and nothing replaced it. A `focus-visible` ring was added globally (`app/globals.css`) |
| Reduced motion | `prefers-reduced-motion: reduce` honoured | Added globally (`app/globals.css`). The design system declares a "bounce" transition, which is a recognised trigger for vestibular disorders |
| Landmarks | One `<header>`, one `<main>`, one `<footer>` per page | Present in all three shells |
| Page headings | Exactly one `<h1>` per page | Present on the application pages. The public forms use a card title (`h3`) inside the public shell and do not have a separate `h1`; see below |
| Navigation | `<nav>` elements carry `aria-label`; the active link carries `aria-current="page"` | Present |
| Mobile navigation toggle | `aria-expanded` and a changing `aria-label` | Present |
| Account menu trigger | Has an accessible name | **Was missing.** The user's name is hidden below the `sm` breakpoint, so the button had no name on a phone. `aria-label` added |
| Form controls | Every input, select, textarea and slider has a `<label for>` or an `aria-label` | Present. Two filters were unlabelled and were given one |
| Error messages | `aria-invalid` plus `aria-describedby` pointing at the message | Present |
| Status messages | `role="status"` for non-urgent results, `role="alert"` for errors | Present |
| Icon-only buttons | `aria-label` naming the action, icons marked `aria-hidden` | Present |
| Progress bars | `aria-label` naming what is being measured | Present |
| Tables | `<caption class="sr-only">` naming the table | Present on the admin tables |
| Colour contrast | Machine-checked with `axe-core`, in both themes | **Verified** — see above |
| Language | `<html lang>` | Present |

---

## What was not verified

Stated plainly, because these are the gaps that remain.

- **No screen-reader pass.** Nothing was tested with NVDA, JAWS, VoiceOver or
  TalkBack. The application uses semantic HTML, labelled controls and live
  regions, which is the necessary foundation, but a screen reader announces
  things a linter cannot predict — the order in which it reads a table, for
  instance, or whether a live region is actually announced. This is the one
  gap the browser suite cannot close, and it needs somebody who uses one.
- **No conformance statement.** WCAG conformance is a claim about a product
  against a specification, and it is made after an audit with assistive
  technology, a contrast tool and a keyboard walkthrough. The second and third
  are done; the first is not, so no claim is made.
- **The public forms have no `h1`.** The sign-in, registration and
  password-reset screens are a card with an `h3` title and no `h1` above it,
  so their heading hierarchy starts at level three. `axe-core` does not fail
  this — the "page has a heading-one" rule is a best-practice rule rather than
  a WCAG one — but it is a real weakness, and the browser suite does not
  currently assert one `h1` per page across the public shell.
- **The suite only walks the routes it names.** A screen that is not in
  `frontend/e2e/helpers.ts` is not axe-checked, and a component that is not
  rendered on those routes is not either. The list is the whole application
  today, and it is a list, not a guarantee.

The honest summary: **the structural work is done and enforced, the machine
checks are done and passing, and the perceptual work — the screen-reader pass
— has not been done.**

---

## What a full audit would still need

In rough order of effort:

1. **A screen-reader pass.** At minimum NVDA on Firefox and VoiceOver on
   Safari, over the register, the CV upload, the recommendations list and the
   skill-gap report — the four journeys that matter. This needs people who use
   screen readers, and no tool substitutes for it.
2. **A `h1` for the public forms.** Each public shell page needs a real
   level-one heading, so the hierarchy does not start at level three.
3. **A wider route sweep.** The axe run covers the routes the suite names. A
   generator that walks the route table would close the gap between "the
   pages we remembered" and "the pages there are".
4. **Then, and only then, a conformance statement** against WCAG 2.2 AA,
   naming the levels that were checked and the ones that were not.
