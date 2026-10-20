import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { cn } from "@/lib/utils"

/**
 * The shadcn slider, with one change that the accessibility suite forced.
 *
 * Radix renders the focusable `role="slider"` element on the **Thumb**, and
 * the Thumb's accessible name comes from the Thumb's own `aria-label`. An
 * `aria-label` on the Root is ignored: with a single value, Radix's own
 * fallback label is `undefined`, so the thumb ends up with no name at all and
 * a screen reader announces a bare slider.
 *
 * Every call site already passes `aria-label` to the Root — it was simply
 * going nowhere. The label is therefore pulled off the Root's props and put on
 * the Thumb, which is where it belongs. The call sites do not change.
 */
const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, "aria-label": ariaLabel, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
      <SliderPrimitive.Range className="absolute h-full bg-primary" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      aria-label={ariaLabel}
      className="block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
    />
  </SliderPrimitive.Root>
))
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
