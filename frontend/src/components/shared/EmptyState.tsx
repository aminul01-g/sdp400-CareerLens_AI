"use client";

/**
 * Empty state.
 *
 * Every list has one. A CRUD screen that renders nothing on an empty list reads as
 * broken, because the user cannot tell "no data yet" from "the request failed".
 * Each use supplies the action that would fill it.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: { label: string; onClick: () => void; variant?: React.ComponentProps<typeof Button>["variant"] };
  secondaryAction?: { label: string; href?: string; onClick?: () => void };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? <div className="text-muted-foreground">{icon}</div> : null}
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {description ? (
          <p className="mx-auto max-w-md text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
        {action ? (
          <Button size="sm" variant={action.variant} onClick={action.onClick}>
            {action.label}
          </Button>
        ) : null}
        {secondaryAction ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={secondaryAction.onClick}
            {...(secondaryAction.href ? { asChild: true } : {})}
          >
            {secondaryAction.label}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
