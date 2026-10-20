"use client";

/**
 * The skip link.
 *
 * A keyboard user arriving on a page with a long navigation has to tab
 * through every link in the header before reaching the content. The skip
 * link is the standard fix: it is the first thing in the tab order, it is
 * invisible until it is focused, and it moves focus straight to the main
 * region.
 *
 * It is a real link rather than a button, because it has a destination and
 * it should work with the browser's own "open in a new tab" behaviour.
 */
export function SkipLink({ targetId = "main-content" }: { targetId?: string }) {
  return (
    <a
      href={`#${targetId}`}
      className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-lg"
    >
      Skip to main content
    </a>
  );
}
