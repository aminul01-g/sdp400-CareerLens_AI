"use client";

/**
 * Element width hook for charts.
 *
 * `recharts` ships a `ResponsiveContainer` that is supposed to do this, and on
 * this project it does not: version 2.13.0 with React 18.3 leaves its internal
 * size state at the `-1` sentinel, so it renders an empty
 * `<div class="recharts-responsive-container">` and the chart never mounts. It
 * logs no warning and throws no error — the container is correctly sized in the
 * DOM (measured 1318x256) while the component's own state stays unset, and
 * dispatching a `resize` event does not recover it. Rather than pin a dependency
 * version on the strength of that, the width is measured here and handed to the
 * chart as a plain number.
 *
 * **This uses a callback ref, not `useRef` + `useEffect([])`, and that detail is
 * the whole reason it works.** These charts sit behind a loading guard, so on the
 * first render the element is not in the tree at all: a `useEffect` with empty
 * deps runs once against `ref.current === null`, returns early, and is never
 * invoked again when the element finally appears. The width would sit at 0
 * forever. A callback ref is invoked by React on attach *and* detach, so the
 * measurement happens at the moment the node actually exists.
 */
import * as React from "react";

interface ChartSize {
  /** Attach to the element that wraps the chart. */
  ref: (node: HTMLDivElement | null) => void;
  /** Measured content width in pixels; 0 until the first measurement lands. */
  width: number;
  height: number;
}

export function useChartSize(height: number): ChartSize {
  const [width, setWidth] = React.useState(0);
  const observerRef = React.useRef<ResizeObserver | null>(null);

  const ref = React.useCallback((node: HTMLDivElement | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;

    if (!node) {
      setWidth(0);
      return;
    }

    const measure = () => {
      // Rounded, so a fractional width cannot retrigger the observer forever.
      const next = Math.round(node.getBoundingClientRect().width);
      setWidth((previous) => (previous === next ? previous : next));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    observerRef.current = observer;
  }, []);

  React.useEffect(() => () => observerRef.current?.disconnect(), []);

  return { ref, width, height };
}
