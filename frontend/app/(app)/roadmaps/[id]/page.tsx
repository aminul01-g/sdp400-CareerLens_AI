"use client";

/**
 * One learning roadmap.
 *
 * The plan is a snapshot: it is shown exactly as it was generated, and the
 * learner's progress is recorded beside it. Nothing on this page rewrites
 * the plan, so a plan somebody is halfway through cannot change underneath
 * them.
 */
import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, CheckCircle2, ExternalLink, FolderGit2, Loader2, Save, Target,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { AiToolsNav } from "@/features/ai/AiToolsNav";
import { useRoadmap, useUpdateRoadmapTask } from "@/lib/hooks/use-ai";

export default function RoadmapDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const plan = useRoadmap(Number.isFinite(id) ? id : null);
  const update = useUpdateRoadmapTask();

  const [drafts, setDrafts] = React.useState<Record<string, { notes: string; url: string }>>({});
  const [saved, setSaved] = React.useState<string | null>(null);

  function draftFor(taskKey: string, notes: string, url: string) {
    return drafts[taskKey] ?? { notes, url };
  }

  async function saveTask(taskKey: string, body: { notes?: string; portfolio_url?: string }) {
    await update.mutateAsync({ roadmapId: id, taskKey, ...body });
    setSaved(taskKey);
    window.setTimeout(() => setSaved(null), 2000);
  }

  async function toggleComplete(taskKey: string, isComplete: boolean) {
    await update.mutateAsync({ roadmapId: id, taskKey, is_complete: isComplete });
  }

  if (plan.isPending) return <LoadingPage label="Loading your learning plan" />;
  if (plan.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Learning plan" />
        <ErrorState error={plan.error} onRetry={() => void plan.refetch()} />
      </div>
    );
  }

  const data = plan.data;
  if (!data) return null;

  const weeks = Array.from(new Set(data.tasks.map((task) => task.week))).sort((a, b) => a - b);

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.title}
        description={
          data.starting_profile ||
          "A plan built from the skills the engine says you are missing."
        }
        actions={
          <Button variant="outline" asChild>
            <Link href="/roadmaps">
              <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
              All plans
            </Link>
          </Button>
        }
      />

      <AiToolsNav />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Progress
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-bold text-primary tabular-nums">
              {data.completed_tasks}/{data.total_tasks}
            </p>
            <Progress value={data.progress_pct} aria-label="Plan progress" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Estimated effort
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums">
              {Math.round(data.total_estimated_hours)}h
            </p>
            <p className="text-sm text-muted-foreground">
              across {data.duration_weeks} weeks
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Target role
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="flex items-center gap-2 font-medium">
              <Target className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              {data.target_role || data.job_role_title}
            </p>
            {data.gap_skills.length > 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">
                Built around {data.gap_skills.length} verified skill gap
                {data.gap_skills.length === 1 ? "" : "s"}.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {data.strengths.length > 0 || data.learning_objectives.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {data.strengths.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Your starting strengths</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {data.strengths.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <CheckCircle2
                        className="mt-0.5 h-4 w-4 shrink-0 text-success"
                        aria-hidden="true"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {data.learning_objectives.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Learning objectives</CardTitle>
                <CardDescription>
                  In priority order. The first one is the most valuable thing to
                  learn next.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ol className="space-y-1 text-sm">
                  {data.learning_objectives.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <span className="font-semibold text-muted-foreground tabular-nums">
                        {index + 1}.
                      </span>
                      {item}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}

      {weeks.map((week) => (
        <section key={week} className="space-y-3">
          <h2 className="text-lg font-semibold">Week {week}</h2>
          {data.tasks
            .filter((task) => task.week === week)
            .map((task) => {
              const draft = draftFor(task.task_key, task.notes, task.portfolio_url);
              return (
                <Card key={task.task_key}>
                  <CardHeader>
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id={`complete-${task.task_key}`}
                        checked={task.is_complete}
                        onCheckedChange={(checked) =>
                          void toggleComplete(task.task_key, checked === true)
                        }
                        aria-label={`Mark "${task.title}" complete`}
                        className="mt-1"
                      />
                      <div className="min-w-0 flex-1 space-y-1">
                        <Label
                          htmlFor={`complete-${task.task_key}`}
                          className="text-base font-medium"
                        >
                          {task.title}
                        </Label>
                        <p className="text-sm text-muted-foreground">{task.objective}</p>
                        <div className="flex flex-wrap gap-2 pt-1">
                          <Badge variant="secondary">
                            {task.estimated_hours}h estimated
                          </Badge>
                          {task.skill_slug ? (
                            <Badge variant="outline">{task.skill_slug}</Badge>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {task.activities.length > 0 ? (
                      <div>
                        <p className="text-sm font-medium">Activities</p>
                        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                          {task.activities.map((item, index) => (
                            <li key={index}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {task.deliverable ? (
                      <p className="text-sm">
                        <span className="font-medium">Deliverable: </span>
                        {task.deliverable}
                      </p>
                    ) : null}

                    {task.completion_criteria.length > 0 ? (
                      <div>
                        <p className="text-sm font-medium">You are done when</p>
                        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                          {task.completion_criteria.map((item, index) => (
                            <li key={index}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {task.resources.length > 0 ? (
                      <div>
                        <p className="text-sm font-medium">Learning resources</p>
                        <ul className="mt-1 space-y-1 text-sm">
                          {task.resources.map((resource) => (
                            <li key={resource.id} className="flex flex-wrap items-center gap-2">
                              <a
                                href={resource.url}
                                target="_blank"
                                rel="noreferrer noopener"
                                className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
                              >
                                {resource.title}
                                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                              </a>
                              <span className="text-muted-foreground">
                                {resource.summary}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {task.portfolio_hint ? (
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium">For your portfolio: </span>
                        {task.portfolio_hint}
                      </p>
                    ) : null}

                    <div className="grid gap-3 border-t pt-3 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label htmlFor={`notes-${task.task_key}`} className="text-sm">
                          Your notes
                        </Label>
                        <Textarea
                          id={`notes-${task.task_key}`}
                          value={draft.notes}
                          onChange={(event) =>
                            setDrafts((previous) => ({
                              ...previous,
                              [task.task_key]: {
                                ...draft,
                                notes: event.target.value,
                              },
                            }))
                          }
                          rows={2}
                          placeholder="What you did, what you learned, what went wrong…"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor={`link-${task.task_key}`} className="text-sm">
                          Link to what you built
                        </Label>
                        <Input
                          id={`link-${task.task_key}`}
                          value={draft.url}
                          onChange={(event) =>
                            setDrafts((previous) => ({
                              ...previous,
                              [task.task_key]: {
                                ...draft,
                                url: event.target.value,
                              },
                            }))
                          }
                          placeholder="https://github.com/you/project"
                          inputMode="url"
                        />
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void saveTask(task.task_key, {
                                notes: draft.notes,
                                portfolio_url: draft.url,
                              })
                            }
                            disabled={update.isPending}
                          >
                            {update.isPending ? (
                              <Loader2
                                className="mr-2 h-3.5 w-3.5 animate-spin"
                                aria-hidden="true"
                              />
                            ) : (
                              <Save className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                            )}
                            Save
                          </Button>
                          {saved === task.task_key ? (
                            <span role="status" className="text-xs text-success">
                              Saved
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
        </section>
      ))}

      {data.portfolio_project ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FolderGit2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              Portfolio project — {data.portfolio_project.title}
            </CardTitle>
            <CardDescription>
              The project that demonstrates the role&apos;s skills. Something you
              can put in a portfolio and be asked about in an interview.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm">
              <span className="font-medium">The problem: </span>
              {data.portfolio_project.problem_statement}
            </p>
            {data.portfolio_project.required_technologies.length > 0 ? (
              <div>
                <p className="text-sm font-medium">Technologies</p>
                <ul className="mt-1 flex flex-wrap gap-1.5">
                  {data.portfolio_project.required_technologies.map((item, index) => (
                    <li key={index}>
                      <Badge variant="outline">{item}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="grid gap-4 md:grid-cols-2">
              {data.portfolio_project.milestones.length > 0 ? (
                <div>
                  <p className="text-sm font-medium">Milestones</p>
                  <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-sm text-muted-foreground">
                    {data.portfolio_project.milestones.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ol>
                </div>
              ) : null}
              {data.portfolio_project.expected_outputs.length > 0 ? (
                <div>
                  <p className="text-sm font-medium">What you should end up with</p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                    {data.portfolio_project.expected_outputs.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
            {data.portfolio_project.evaluation_criteria.length > 0 ? (
              <div>
                <p className="text-sm font-medium">How it is judged</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                  {data.portfolio_project.evaluation_criteria.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {data.portfolio_presentation.length > 0 ? (
              <div>
                <p className="text-sm font-medium">Showing the work</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                  {data.portfolio_presentation.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {data.notes ? (
        <Alert>
          <AlertDescription>{data.notes}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex justify-end">
        <Button variant="ghost" onClick={() => router.push("/roadmaps")}>
          Back to all plans
        </Button>
      </div>
    </div>
  );
}
