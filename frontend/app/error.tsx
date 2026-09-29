"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/client";

/** Segment-level render-failure boundary. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Unhandled render error", error);
  }, [error]);

  return (
    <div className="container mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold">Something went wrong</h1>
      <p className="text-muted-foreground">{errorMessage(error, "This page could not be displayed.")}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
