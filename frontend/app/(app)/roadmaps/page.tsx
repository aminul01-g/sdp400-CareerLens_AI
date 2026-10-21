"use client";

/**
 * Learning roadmaps.
 *
 * A roadmap is generated from the engine's own gap report for one role and
 * then saved, so a learner can come back to it. This screen lists the saved
 * ones and generates a new one; the detail screen is where the work happens.
 *
 * Generation is a mutation, never a query: every call reaches the model
 * provider and costs money, so it happens when the user asks for it and not
 * when the page opens.
 */
import * as React from "react";
import Link from "next/link";
import { CalendarClock, Loader2, Plus, Route } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { AiToolsNav } from "@/features/ai/AiToolsNav";
import { AiUnavailable } from "@/features/ai/AiUnavailable";
import { StoredLanguageToggle, usePreferredLanguage } from "@/features/ai/LanguageToggle";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import { useAiStatus, useGenerateRoadmap, useRoadmaps } from "@/lib/hooks/use-ai";
import { useJobRoles } from "@/lib/hooks/use-jobs";

export default function RoadmapsPage() {
  const status = useAiStatus();
  const roadmaps = useRoadmaps();
  const roles = useJobRoles();
  const generate = useGenerateRoadmap();

  const [roleId, setRoleId] = React.useState<number | null>(null);
  const [weeks, setWeeks] = React.useState<4 | 6>(4);
  const [language, setLanguage] = React.useState<"en" | "bn">("en");
  const preferred = usePreferredLanguage();
  const [formError, setFormError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLanguage(preferred);
  }, [preferred]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, { id: number; title: string }[]>();
    for (const role of roles.data?.items ?? []) {
      const bucket = map.get(role.family) ?? [];
      bucket.push({ id: role.id, title: role.title });
      map.set(role.family, bucket);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [roles.data]);

  async function create() {
    if (roleId == null) {
      setFormError("Choose a role first.");
      return;
    }
    setFormError(null);
    try {
      const plan = await generate.mutateAsync({
        job_role_id: roleId,
        duration_weeks: weeks,
        language,
      });
      window.location.assign(`/roadmaps/${plan.id}`);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError && caught.status === 503
          ? "The AI assistant is not enabled on this deployment."
          : errorMessage(caught, "The learning plan could not be generated."),
      );
    }
  }

  if (status.isPending) return <LoadingPage label="Checking the AI assistant" />;

  const enabled = status.data?.enabled === true;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Learning roadmaps"
        description="A four- or six-week plan for one role, built from the skills the engine says you are missing, with a portfolio project to show for it."
        actions={<StoredLanguageToggle value={language} onChange={setLanguage} />}
      />

      <AiToolsNav />

      {!enabled ? (
        <AiUnavailable feature="generate a learning plan" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Route className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Plan a new roadmap
              </CardTitle>
              <CardDescription>
                The plan targets the verified skill gaps for the role you pick,
                and gives every task a completion criterion you can check.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {formError ? (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label
                    htmlFor="roadmap-role"
                    className="text-sm font-medium leading-none"
                  >
                    Target role
                  </label>
                  <Select
                    value={roleId != null ? String(roleId) : undefined}
                    onValueChange={(value) => setRoleId(Number(value))}
                  >
                    <SelectTrigger id="roadmap-role" aria-label="Choose a target role">
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
                </div>

                <div className="space-y-1.5">
                  <span className="text-sm font-medium leading-none">Length</span>
                  <div
                    role="group"
                    aria-label="Length of the plan"
                    className="inline-flex rounded-md border p-0.5"
                  >
                    {([4, 6] as const).map((value) => (
                      <Button
                        key={value}
                        type="button"
                        size="sm"
                        variant={weeks === value ? "default" : "ghost"}
                        aria-pressed={weeks === value}
                        onClick={() => setWeeks(value)}
                      >
                        {value} weeks
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              <Button
                onClick={() => void create()}
                disabled={generate.isPending || roleId == null}
              >
                {generate.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                )}
                {generate.isPending ? "Building your plan…" : "Generate the plan"}
              </Button>
            </CardContent>
          </Card>

          {roadmaps.isPending ? (
            <LoadingPage label="Loading your saved plans" />
          ) : roadmaps.isError ? (
            <ErrorState
              error={roadmaps.error}
              onRetry={() => void roadmaps.refetch()}
            />
          ) : (roadmaps.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              icon={<Route className="h-8 w-8" aria-hidden="true" />}
              title="No learning plans yet"
              description="Pick a role above and generate a plan. It is saved, so you can mark tasks complete and come back to it later."
            />
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2">
              {roadmaps.data?.items.map((plan) => (
                <li key={plan.id}>
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="text-base">
                        <Link
                          href={`/roadmaps/${plan.id}`}
                          className="underline-offset-4 hover:underline"
                        >
                          {plan.title}
                        </Link>
                      </CardTitle>
                      <CardDescription className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{plan.duration_weeks} weeks</Badge>
                        <span className="inline-flex items-center gap-1 text-xs">
                          <CalendarClock
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                          />
                          {new Date(plan.created_at).toLocaleDateString()}
                        </span>
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="font-medium tabular-nums">
                          {plan.completed_tasks} of {plan.total_tasks} tasks
                        </span>
                      </div>
                      <Progress value={plan.progress_pct} aria-label="Plan progress" />
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
