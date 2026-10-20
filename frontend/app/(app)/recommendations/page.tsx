"use client";

/**
 * Recommendations.
 *
 * The product's payoff. Two deliberate choices:
 *
 * 1. **Generation is a mutation triggered by a button**, never a query that fires
 *    on mount. A query would run the whole engine and append a row to the user's
 *    run history every time the page was opened.
 * 2. **A role with a zero score is still listed.** Dropping it would make the
 *    candidate set look curated when it is not; "MLOps Engineer, 3% — you have
 *    almost none of the required skills" is actionable information.
 */
import * as React from "react";
import Link from "next/link";
import {
  Bookmark, ChevronDown, History, Loader2, RefreshCw, Sparkles, Target, ThumbsDown,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingCards, LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import type { RecommendationResponse, RoleRecommendation } from "@/lib/api/types";
import {
  OUTCOME_ACTIONS, OUTCOME_LABELS, type FeedbackAction,
} from "@/lib/api/recommendations";
import { useJobFamilies } from "@/lib/hooks/use-jobs";
import {
  useGenerateRecommendations, useRecordFeedback, useRuns,
} from "@/lib/hooks/use-recommendations";
import { useUserSkills } from "@/lib/hooks/use-skills";
import { ScoreBreakdown } from "@/features/recommendations/ScoreBreakdown";

export default function RecommendationsPage() {
  const [result, setResult] = React.useState<RecommendationResponse | null>(null);
  const [family, setFamily] = React.useState<string>("all");
  const [limit, setLimit] = React.useState(10);

  const skills = useUserSkills();
  const families = useJobFamilies();
  const runs = useRuns();
  const generate = useGenerateRecommendations();

  const hasSkills = (skills.data?.length ?? 0) > 0;
  const needsSkills = !skills.isPending && !hasSkills;

  async function handleGenerate() {
    try {
      const response = await generate.mutateAsync({
        limit,
        role_family: family === "all" ? null : family,
      });
      setResult(response);
    } catch (error) {
      if (error instanceof ApiError && error.code === "profile_incomplete") {
        // 409 with a real next step, not a dead end.
        setResult(null);
      }
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recommendations"
        description="Your ranked AI/ML roles, with every score decomposed into the two components that produced it."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Select value={String(limit)} onValueChange={(value) => setLimit(Number(value))}>
              <SelectTrigger className="w-28" aria-label="Number of roles to show">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[5, 10, 20, 50].map((n) => (
                  <SelectItem key={n} value={String(n)}>Top {n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={family} onValueChange={setFamily}>
              <SelectTrigger className="w-52" aria-label="Filter by role family">
                <SelectValue placeholder="All families" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All role families</SelectItem>
                {(families.data ?? []).map((f) => (
                  <SelectItem key={f.family} value={f.family}>
                    {f.family} ({f.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => void handleGenerate()} disabled={generate.isPending || !hasSkills}>
              {generate.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : result ? (
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {generate.isPending ? "Ranking roles…" : result ? "Run again" : "Generate recommendations"}
            </Button>
          </div>
        }
      />

      {needsSkills ? (
        <EmptyState
          icon={<Target className="h-8 w-8" aria-hidden="true" />}
          title="Add at least one skill first"
          description="The engine scores you by comparing your skills against each role's requirements. With no skills every role would score zero, which tells you nothing."
          action={{ label: "Add skills", onClick: () => { window.location.href = "/skills"; } }}
          secondaryAction={{ label: "Upload your CV", href: "/resume" }}
        />
      ) : null}

      {generate.isError && !(generate.error instanceof ApiError && generate.error.code === "profile_incomplete") ? (
        <ErrorState error={generate.error} onRetry={() => void handleGenerate()} />
      ) : null}

      {generate.isError && generate.error instanceof ApiError && generate.error.code === "profile_incomplete" ? (
        <Alert role="status">
          <AlertDescription className="flex items-center justify-between gap-3">
            {generate.error.message}
            <Button asChild size="sm" variant="outline">
              <Link href="/skills">Go to skills</Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {generate.isPending ? <LoadingCards count={3} /> : null}

      {result ? (
        <section className="space-y-4" aria-labelledby="results-heading">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="results-heading" className="text-lg font-semibold">
              {result.results.length} of {result.total_candidates} roles
            </h2>
            <p className="text-sm text-muted-foreground">
              {result.weights.skill_coverage} × coverage + {result.weights.tfidf_similarity} × cosine
              · engine {result.engine_version} ·{" "}
              <Link href={`/recommendations/${result.run_id}`} className="text-primary hover:underline">
                view this run
              </Link>
            </p>
          </div>

          {result.results.length === 0 ? (
            <EmptyState
              title="No roles matched those filters"
              description="Try a different role family, or generate against all of them."
              action={{ label: "Generate again", onClick: () => void handleGenerate() }}
            />
          ) : (
            <div className="space-y-3">
              {result.results.map((role) => (
                <RecommendationCard key={role.job_role_id} role={role} runId={result.run_id} />
              ))}
            </div>
          )}
        </section>
      ) : null}

      {!result && !generate.isPending && !needsSkills ? (
        <Card>
          <CardHeader>
            <CardTitle>No run yet</CardTitle>
            <CardDescription>
              Generating is deliberate rather than automatic: it runs the full engine and
              records a run in your history, so it should be something you ask for.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void handleGenerate()}>
              <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
              Generate recommendations
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <section aria-labelledby="history-heading" className="space-y-3">
        <h2 id="history-heading" className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          <History className="h-4 w-4" aria-hidden="true" />
          Run history
        </h2>
        {runs.isPending ? (
          <LoadingRows count={2} />
        ) : runs.isError ? (
          <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
        ) : (runs.data?.items ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">No runs yet. Your first one will appear here.</p>
        ) : (
          <ul className="divide-y rounded-md border">
            {runs.data?.items.map((run) => (
              <li key={run.id}>
                <Link
                  href={`/recommendations/${run.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm hover:bg-accent"
                >
                  <span className="font-medium">
                    {run.top_role_title ?? "No top role"}
                    {run.top_compatibility != null ? (
                      <span className="ml-2 font-semibold text-primary">{run.top_compatibility}%</span>
                    ) : null}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(run.created_at).toLocaleString()} · {run.total_candidates} candidates
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function RecommendationCard({
  role,
  runId,
}: {
  role: RoleRecommendation;
  runId: number;
}) {
  const [open, setOpen] = React.useState(false);
  const [action, setAction] = React.useState<FeedbackAction | null>(null);
  const record = useRecordFeedback(runId);
  const topMatched = role.matched_skills.slice(0, 3);
  const topMissing = role.missing_skills.slice(0, 3);

  function mark(next: FeedbackAction) {
    setAction(next);
    record.mutate({ jobRoleId: role.job_role_id, action: next });
  }

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-muted-foreground">#{role.rank}</span>
              <h3 className="text-lg font-semibold">{role.title}</h3>
              <Badge variant="outline">{role.family}</Badge>
              {role.seniority ? <Badge variant="secondary">{role.seniority}</Badge> : null}
            </div>
            <p className="text-sm text-muted-foreground">
              {role.matched_skills.length} matched · {role.missing_skills.length} missing of{" "}
              {role.matched_skills.length + role.missing_skills.length} required
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-primary">{role.compatibility_pct}%</p>
            <p className="text-xs text-muted-foreground">compatibility</p>
          </div>
        </div>

        <Progress value={role.compatibility_pct} className="mt-4" aria-label={`${role.title}: ${role.compatibility_pct}% compatible`} />

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Top matched
            </p>
            {topMatched.length === 0 ? (
              <p className="text-sm text-muted-foreground">None of this role&apos;s requirements are covered.</p>
            ) : (
              <ul className="space-y-1">
                {topMatched.map((skill) => (
                  <li key={skill.skill_id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">{skill.name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      weight {skill.weight} · you {skill.proficiency}/5
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Top missing
            </p>
            {topMissing.length === 0 ? (
              <p className="text-sm text-muted-foreground">You cover every requirement.</p>
            ) : (
              <ul className="space-y-1">
                {topMissing.map((skill) => (
                  <li key={skill.skill_id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">{skill.name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">weight {skill.weight}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            <ChevronDown className={`mr-1.5 h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
            How this score was calculated
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/skill-gap?role=${role.job_role_id}`}>Skill gap</Link>
          </Button>

          <div className="ml-auto flex items-center gap-2">
            <Button
              variant={action === "saved" ? "default" : "ghost"}
              size="sm"
              disabled={record.isPending}
              onClick={() => mark("saved")}
              aria-pressed={action === "saved"}
            >
              <Bookmark className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {action === "saved" ? "Saved" : "Save"}
            </Button>
            <Button
              variant={action === "dismissed" ? "secondary" : "ghost"}
              size="sm"
              disabled={record.isPending}
              onClick={() => mark("dismissed")}
              aria-pressed={action === "dismissed"}
            >
              <ThumbsDown className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {action === "dismissed" ? "Not for me" : "Not for me"}
            </Button>
          </div>
        </div>

        {/*
          The outcome row. These are the user's own reports of what happened
          after they left the shortlist, and they are weighted above the
          buttons above: a role somebody got an interview for is better
          evidence of a good match than a role somebody saved. The
          application cannot observe any of this — the user tells it, and
          the community prior counts the report.
        */}
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
          <span className="text-xs text-muted-foreground">How did it go?</span>
          {OUTCOME_ACTIONS.map((outcome) => (
            <Button
              key={outcome}
              variant={action === outcome ? "default" : "outline"}
              size="sm"
              disabled={record.isPending}
              onClick={() => mark(outcome)}
              aria-pressed={action === outcome}
            >
              {OUTCOME_LABELS[outcome]}
            </Button>
          ))}
        </div>

        {role.feedback_samples > 0 ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {role.feedback_samples} other user{role.feedback_samples === 1 ? "" : "s"} have
            said something about this role
            {role.role_prior !== 0
              ? `, and it has moved the score by ${(role.role_prior * 10).toFixed(1)}%`
              : ""}
            .
          </p>
        ) : null}

        {open ? <ScoreBreakdown role={role} /> : null}
      </CardContent>
    </Card>
  );
}
