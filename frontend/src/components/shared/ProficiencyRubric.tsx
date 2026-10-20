"use client";

/**
 * The proficiency rubric, next to the control that asks for it.
 *
 * A self-reported level is only comparable if everyone means the same thing by
 * it. The full rubric lives in `docs/proficiency-rubric.md`; this component
 * shows the level names and what each one means, so the user does not have to
 * guess what "3" is supposed to represent.
 */
import * as React from "react";
import { BookOpen } from "lucide-react";
import { PROFICIENCY_LEVELS } from "@/lib/rubric";

export function ProficiencyRubric({ className = "" }: { className?: string }) {
  return (
    <details className={`rounded-md border bg-muted/20 p-3 ${className}`}>
      <summary className="flex cursor-pointer items-center gap-2 text-sm font-medium">
        <BookOpen className="h-4 w-4" aria-hidden="true" />
        What each level means
      </summary>
      <dl className="mt-3 space-y-2 text-sm">
        {PROFICIENCY_LEVELS.map((entry) => (
          <div key={entry.level} className="flex gap-3">
            <dt className="w-24 shrink-0 font-semibold">
              {entry.level} — {entry.name}
            </dt>
            <dd className="text-muted-foreground">
              {entry.can}
              {entry.cannot !== "—" ? (
                <span className="block text-xs">Not yet: {entry.cannot.toLowerCase()}</span>
              ) : null}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">
        Levels are judged on what you can do unaided, not on how long you have used
        something. The full rubric is in <code>docs/proficiency-rubric.md</code>.
      </p>
    </details>
  );
}
