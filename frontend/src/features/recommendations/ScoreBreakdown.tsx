"use client";

import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import type { RoleRecommendation } from "@/lib/api/types";

/**
 * The score decomposition.
 *
 * Both components, both weights, and the formula, rendered literally. A percentage
 * the user cannot reconstruct is not an explanation — this is the proposal's
 * "explain each score with matched skills" requirement, made checkable.
 *
 * The coverage component is itself a derivation now, so it is shown as one:
 *
 *   declared coverage  →  recency & depth  →  level fit  →  skill coverage
 *
 * and the headline formula is unchanged:
 *
 *   0.6 × skill coverage + 0.4 × text similarity
 *
 * A user who has stated no recency, depth or level sees 1.000 on every
 * adjustment, and the display collapses back to the two-component form.
 */
export function ScoreBreakdown({ role }: { role: RoleRecommendation }) {
  const hasSignalAdjustment =
    Math.abs(role.declared_coverage - role.signal_coverage) > 0.0001;
  const hasLevelAdjustment = Math.abs(role.level_fit - 1) > 0.0001;

  return (
    <div className="mt-4 space-y-4 rounded-md border bg-muted/30 p-4">
      <p className="text-sm font-medium">Score breakdown</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span>Weighted skill coverage</span>
            <span className="font-semibold">{role.skill_coverage.toFixed(3)}</span>
          </div>
          <Progress value={role.skill_coverage * 100} aria-label="Weighted skill coverage" />
          <p className="text-xs text-muted-foreground">
            Share of the role&apos;s weighted requirements you satisfy, scaled by your
            proficiency on each. Contributes {role.coverage_contribution.toFixed(3)}.
          </p>

          {hasSignalAdjustment || hasLevelAdjustment ? (
            <dl className="space-y-1 border-l-2 pl-3 text-xs text-muted-foreground">
              <div className="flex justify-between gap-2">
                <dt>You declared</dt>
                <dd className="font-mono">{role.declared_coverage.toFixed(3)}</dd>
              </div>
              {hasSignalAdjustment ? (
                <div className="flex justify-between gap-2">
                  <dt>After recency and depth</dt>
                  <dd className="font-mono">{role.signal_coverage.toFixed(3)}</dd>
                </div>
              ) : null}
              {hasLevelAdjustment ? (
                <div className="flex justify-between gap-2">
                  <dt>Level fit ({role.seniority ?? "unlabelled"} role)</dt>
                  <dd className="font-mono">× {role.level_fit.toFixed(3)}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span>TF-IDF cosine similarity</span>
            <span className="font-semibold">{role.tfidf_similarity.toFixed(3)}</span>
          </div>
          <Progress value={role.tfidf_similarity * 100} aria-label="TF-IDF cosine similarity" />
          <p className="text-xs text-muted-foreground">
            Lexical similarity between your profile text and this role&apos;s description.
            Contributes {role.tfidf_contribution.toFixed(3)}.
          </p>
        </div>
      </div>

      <p className="rounded bg-background p-2 font-mono text-xs">
        {role.coverage_contribution.toFixed(3)} + {role.tfidf_contribution.toFixed(3)} ={" "}
        {(role.compatibility_pct / 100).toFixed(3)} → {role.compatibility_pct}%
      </p>

      {role.feedback_samples > 0 ? (
        <p className="text-xs text-muted-foreground">
          {role.feedback_samples} user{role.feedback_samples === 1 ? "" : "s"} have said
          something about this role, giving a community prior of{" "}
          <span className="font-mono">{role.role_prior.toFixed(3)}</span>, which moved the
          score by {(role.role_prior * 10).toFixed(1)}%.
        </p>
      ) : null}

      {role.missing_skills.some((s) => s.weight >= 0.8) ? (
        <Alert>
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          <AlertDescription>
            You are missing at least one <strong>critical</strong> requirement (importance 0.8
            or more). That is usually worth more than any amount of additional breadth.
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
