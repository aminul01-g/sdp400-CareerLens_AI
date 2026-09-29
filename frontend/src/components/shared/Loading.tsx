"use client";

/**
 * Loading skeletons.
 *
 * Sized to the real layout rather than a centred spinner over a blank page: a
 * spinner hides the fact that the page has a shape, and the layout shift when the
 * data arrives is worse than the wait. The plan calls skeletons out specifically.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} className={cn("h-4", index === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

export function LoadingCards({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("grid gap-4 md:grid-cols-2 lg:grid-cols-3", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="rounded-lg border p-4 space-y-3">
          <Skeleton className="h-5 w-2/3" />
          <SkeletonText lines={2} />
        </div>
      ))}
    </div>
  );
}

export function LoadingRows({ count = 5, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
    </div>
  );
}

export function LoadingPage({ label = "Loading" }: { label?: string }) {
  return (
    <div className="space-y-6" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
      <div className="space-y-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      <LoadingCards />
    </div>
  );
}
