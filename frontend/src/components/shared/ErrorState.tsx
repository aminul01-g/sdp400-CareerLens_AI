"use client";

/**
 * Error state with a retry affordance.
 *
 * Shows the server's own message when there is one, because a 409 "that email is
 * already registered" is actionable and a generic "something went wrong" is not.
 * `401` is called out separately: it means the session ended, and the right action
 * is to sign in again rather than to retry.
 */
import * as React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
  className?: string;
}

export function ErrorState({ error, onRetry, title, className }: ErrorStateProps) {
  const isUnauthorized = error instanceof ApiError && error.isUnauthorized;
  const isForbidden = error instanceof ApiError && error.isForbidden;

  const heading =
    title ??
    (isUnauthorized
      ? "Your session has ended"
      : isForbidden
        ? "You do not have access to this"
        : "We could not load this");

  const detail = isUnauthorized
    ? "Please sign in again to continue."
    : errorMessage(error, "An unexpected error occurred. Please try again.");

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`flex flex-col items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-6 ${className ?? ""}`}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-medium text-destructive">{heading}</p>
          <p className="text-sm text-muted-foreground">{detail}</p>
        </div>
      </div>
      {onRetry && !isUnauthorized ? (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
          Try again
        </Button>
      ) : null}
      {isUnauthorized ? (
        <Button size="sm" asChild>
          <a href="/login">Sign in</a>
        </Button>
      ) : null}
    </div>
  );
}
