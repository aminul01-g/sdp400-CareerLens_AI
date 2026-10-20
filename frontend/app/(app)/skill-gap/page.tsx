"use client";

/**
 * Skill-gap analysis for a target role.
 *
 * The ordering is the feature: missing skills are shown strictly by descending
 * importance weight, banded into critical / important / desirable, so the first row
 * is the single most valuable thing to learn next. That is the proposal's
 * "ranked by their importance weight for that role" made visible.
 *
 * The band thresholds (0.8 and 0.5) are the same constants the engine uses, so
 * the badge can never drift from the sort order.
 */
import * as React from "react";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Award, CheckCircle2, GraduationCap, Loader2, Target } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import type { LearningPath, Tier } from "@/lib/api/types";
import { useJobRoles } from "@/lib/hooks/use-jobs";
import { useSkillGap } from "@/lib/hooks/use-skill-gap";
import { useUserSkills } from "@/lib/hooks/use-skills";

const TIER_STYLE: Record<Tier, { label: string; className: string }> = {
  critical: {
    label: "Critical",
    className: "bg-destructive-surface/15 text-destructive border-destructive-surface/30",
  },
  important: { label: "Important", className: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30" },
  desirable: { label: "Desirable", className: "bg-muted text-muted-foreground" },
};

function SkillGapContent() {
  const searchParams = useSearchParams();
  const [selected, setSelected] = React.useState<number | null>(null);

  const roles = useJobRoles();
  const skills = useUserSkills();
  const gap = useSkillGap(selected);

  // The recommendations page deep-links here with ?role=<id>.
  React.useEffect(() => {
    const fromQuery = Number(searchParams.get("role"));
    if (Number.isFinite(fromQuery) && fromQuery > 0) setSelected(fromQuery);
  }, [searchParams]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, typeof roles.data extends { items: infer I } ? I : never>();
    for (const role of roles.data?.items ?? []) {
      const bucket = map.get(role.family) ?? [];
      bucket.push(role);
      map.set(role.family, bucket);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [roles.data]);

  const skillCount = skills.data?.length ?? 0;

  if (roles.isPending) return <LoadingPage label="Loading job roles" />;
  if (roles.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Skill gap" />
        <ErrorState error={roles.error} onRetry={() => void roles.refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Skill gap"
        description="Pick a target role and see exactly which of its required skills you are missing, ranked by how much that role values them."
        actions={
          <Select
            value={selected != null ? String(selected) : undefined}
            onValueChange={(value) => setSelected(Number(value))}
          >
            <SelectTrigger className="w-72" aria-label="Choose a target role">
              <SelectValue placeholder="Choose a target role" />
            </SelectTrigger>
            <SelectContent className="max-h-96">
              {grouped.map(([family, familyRoles]) => (
                <SelectGroup key={family}>
                  <SelectLabel>{family}</SelectLabel>
                  {familyRoles.map((role) => (
                    <SelectItem key={role.id} value={String(role.id)}>
                      {role.title}
                    </SelectItem>
                  ))}
                </SelectGroup>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {skillCount === 0 ? (
        <Alert>
          <AlertDescription className="flex items-center justify-between gap-3">
            You have no confirmed skills, so every role will show a full gap.{" "}
            <Button asChild size="sm" variant="outline">
              <Link href="/skills">Add skills</Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {selected == null ? (
        <EmptyState
          icon={<Target className="h-8 w-8" aria-hidden="true" />}
          title="Choose a target role"
          description={`There are ${roles.data?.total ?? 0} AI/ML roles in the knowledge base. Pick one to see the gap.`}
        />
      ) : gap.isPending ? (
        <LoadingPage label={`Analysing the gap for this role`} />
      ) : gap.isError ? (
        <ErrorState error={gap.error} onRetry={() => void gap.refetch()} />
      ) : (
        <GapReportView roleId={selected} />
      )}
    </div>
  );
}

function GapReportView({ roleId }: { roleId: number }) {
  // Reads the same query key the parent already populated, so this is a cache hit
  // rather than a second request.
  const gap = useSkillGap(roleId);
  const data = gap.data;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <Card className="border-primary/30">
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2 text-xl">
            {data.job_role.title}
            <Badge variant="outline">{data.job_role.family}</Badge>
            {data.job_role.seniority ? <Badge variant="secondary">{data.job_role.seniority}</Badge> : null}
          </CardTitle>
          <CardDescription>
            You cover {data.matched_count} of {data.required_count} required skills.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-end gap-3">
            <p className="text-4xl font-bold text-primary">{data.coverage_pct}%</p>
            <p className="pb-1 text-sm text-muted-foreground">weighted skill coverage</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <Badge variant="outline">{data.matched_count} matched</Badge>
            <Badge variant={data.missing_count > 0 ? "secondary" : "outline"}>
              {data.missing_count} missing
            </Badge>
            {data.tiers.critical > 0 ? (
              <Badge className={TIER_STYLE.critical.className}>{data.tiers.critical} critical</Badge>
            ) : null}
            {data.tiers.important > 0 ? (
              <Badge className={TIER_STYLE.important.className}>{data.tiers.important} important</Badge>
            ) : null}
            {data.tiers.desirable > 0 ? (
              <Badge className={TIER_STYLE.desirable.className}>{data.tiers.desirable} desirable</Badge>
            ) : null}
          </div>
          {data.learning_path_available ? (
            <LearningPathCard roleId={data.job_role.job_role_id} />
          ) : null}
        </CardContent>
      </Card>

      <section className="space-y-3" aria-labelledby="missing-heading">
        <h2 id="missing-heading" className="text-lg font-semibold">
          What to learn next
        </h2>
        {data.missing.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 className="h-8 w-8 text-emerald-700" aria-hidden="true" />}
            title="You already cover every required skill"
            description="This role has no gaps in terms of which skills you hold. Coverage is still below 100% if any of your proficiencies are below maximum — raising those is the remaining lever here."
          />
        ) : (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <caption className="sr-only">
                    Skills required by {data.job_role.title} that you do not hold, ordered by
                    importance weight
                  </caption>
                  <thead className="border-b bg-muted/50">
                    <tr>
                      <th scope="col" className="w-12 px-4 py-3 text-left font-medium">#</th>
                      <th scope="col" className="px-4 py-3 text-left font-medium">Skill</th>
                      <th scope="col" className="px-4 py-3 text-left font-medium">Category</th>
                      <th scope="col" className="w-32 px-4 py-3 text-left font-medium">Importance</th>
                      <th scope="col" className="w-28 px-4 py-3 text-left font-medium">Tier</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.missing.map((skill, index) => (
                      <tr key={skill.skill_id}>
                        <td className="px-4 py-3 text-muted-foreground">{index + 1}</td>
                        <td className="px-4 py-3 font-medium">{skill.name}</td>
                        <td className="px-4 py-3 text-muted-foreground">{skill.category ?? "—"}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 rounded-full bg-muted">
                              <div className="h-1.5 rounded-full bg-primary" style={{ width: `${skill.weight * 100}%` }} />
                            </div>
                            <span className="tabular-nums">{skill.weight.toFixed(2)}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className={TIER_STYLE[skill.tier].className}>
                            {TIER_STYLE[skill.tier].label}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </section>

      <section className="space-y-3" aria-labelledby="matched-heading">
        <h2 id="matched-heading" className="text-lg font-semibold">
          What you already have
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.matched.map((skill) => (
            <Card key={skill.skill_id}>
              <CardContent className="space-y-1.5 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{skill.name}</p>
                  <Badge variant={skill.proficiency >= 4 ? "secondary" : "outline"}>
                    {skill.proficiency}/5
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">{skill.category ?? "—"}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>weight {skill.weight.toFixed(2)}</span>
                  <span>·</span>
                  <span>contributes {skill.contribution.toFixed(3)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * The optional LLM learning path.
 *
 * Rendered only when the API says it is available, and it handles `503` as an
 * expected outcome rather than an error: the flag is off by default and nothing
 * else may look broken because of it.
 */
function LearningPathCard({ roleId }: { roleId: number }) {
  const [steps, setSteps] = React.useState<LearningPath["steps"] | null>(null);
  const [state, setState] = React.useState<"idle" | "loading" | "unavailable" | "error">("idle");

  async function request() {
    setState("loading");
    try {
      const { skillGapApi } = await import("@/lib/api/skillGap");
      const response = await skillGapApi.learningPath(roleId);
      setSteps(response.steps);
      setState("idle");
    } catch (error) {
      setState(error instanceof ApiError && error.status === 503 ? "unavailable" : "error");
    }
  }

  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <GraduationCap className="h-4 w-4" aria-hidden="true" />
          Learning path (optional)
        </CardTitle>
        <CardDescription>
          An LLM can turn the missing-skill list into a short study plan. The core gap report
          above is complete without it.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {state === "unavailable" ? (
          <p className="text-sm text-muted-foreground">
            The learning-path feature is disabled on this deployment, so no learning path is
            available. Everything above is unaffected.
          </p>
        ) : steps ? (
          <ol className="space-y-2">
            {steps.map((step) => (
              <li key={step.skill_id} className="flex gap-3 text-sm">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {step.order}
                </span>
                <span>
                  <span className="font-medium">{step.skill_name}</span>
                  <Badge variant="outline" className={`ml-2 ${TIER_STYLE[step.tier].className}`}>
                    {TIER_STYLE[step.tier].label}
                  </Badge>
                  <span className="block text-muted-foreground">{step.guidance}</span>
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <>
            <Button size="sm" variant="outline" onClick={() => void request()} disabled={state === "loading"}>
              {state === "loading" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : <Award className="mr-2 h-4 w-4" aria-hidden="true" />}
              Generate a learning path
            </Button>
            {state === "error" ? (
              <p className="text-sm text-destructive">
                That did not work. The skill gap above is unaffected.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** `useSearchParams` (for the `?role=` deep link) requires a Suspense boundary. */
export default function SkillGapPage() {
  return (
    <Suspense fallback={<LoadingPage label="Loading the skill gap" />}>
      <SkillGapContent />
    </Suspense>
  );
}
