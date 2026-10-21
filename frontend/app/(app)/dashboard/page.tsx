"use client";

/**
 * Dashboard.
 *
 * Every figure on this page is a real aggregate from `GET /api/dashboard/summary`
 * and `GET /api/dashboard/completeness`. The predecessor's dashboard rendered
 * `totalUsers: "12,847"`, `successRate: "94%"`, `careerPaths: "500+"` and
 * `averageCompletion: "18 minutes"`, plus a `setTimeout` that faked loading. All of
 * that is deleted, not restyled.
 */
import * as React from "react";
import Link from "next/link";
import {
  Award, CheckCircle2, Circle, ClipboardList, FileSearch, FileText, FolderGit2,
  GraduationCap, LayoutDashboard, MessagesSquare, Route, Sparkles, Target, TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAuth } from "@/components/providers/AuthProvider";
import { useAiStatus } from "@/lib/hooks/use-ai";
import { useDashboardSummary, useProfileCompleteness } from "@/lib/hooks/use-dashboard";

/** The AI workspace's four entry points, shown on the dashboard. */
const aiTools = [
  {
    href: "/mentor",
    label: "Career mentor",
    description: "Ask questions about your career and get answers from your own record.",
    icon: MessagesSquare,
  },
  {
    href: "/roadmaps",
    label: "Learning roadmap",
    description: "A four- or six-week plan with a portfolio project to show for it.",
    icon: Route,
  },
  {
    href: "/job-analysis",
    label: "Job analysis",
    description: "Paste a job description and see which requirements you already meet.",
    icon: FileSearch,
  },
  {
    href: "/interview",
    label: "Mock interview",
    description: "Practise against a role and get structured feedback on each answer.",
    icon: ClipboardList,
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const summary = useDashboardSummary();
  const completeness = useProfileCompleteness();
  const aiStatus = useAiStatus();

  const aiEnabled = aiStatus.data?.enabled === true;

  if (summary.isPending || completeness.isPending) return <LoadingPage label="Loading your dashboard" />;

  if (summary.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Dashboard" />
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      </div>
    );
  }

  const stats = summary.data;
  const progress = completeness.data;

  const metrics = [
    { label: "Skills", value: stats.skills_count, href: "/skills", icon: Target },
    { label: "Projects", value: stats.projects_count, href: "/projects", icon: FolderGit2 },
    { label: "Education", value: stats.education_count, href: "/education", icon: GraduationCap },
    { label: "Certifications", value: stats.certifications_count, href: "/certifications", icon: Award },
    { label: "CV uploads", value: stats.resume_uploads_count, href: "/resume", icon: FileText },
    { label: "Recommendation runs", value: stats.total_recommendation_runs, href: "/recommendations", icon: TrendingUp },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] ?? "there"}`}
        description={
          stats.latest_run_at
            ? `Your last recommendation run was ${new Date(stats.latest_run_at).toLocaleDateString()}.`
            : "Build your profile and generate your first recommendation run."
        }
        actions={
          <Button asChild>
            <Link href="/recommendations">
              <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
              {stats.total_recommendation_runs ? "Generate again" : "Get recommendations"}
            </Link>
          </Button>
        }
      />

      {stats.top_role_title ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <LayoutDashboard className="h-5 w-5 text-primary" aria-hidden="true" />
              Your latest top match
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xl font-semibold">{stats.top_role_title}</p>
              {/* Not `text-muted-foreground`: on this tinted card it lands at
                  4.42:1, just under the 4.5:1 that WCAG AA asks for. The
                  browser suite caught it once a user had a recommendation
                  run, which is the normal state rather than an edge case. */}
              <p className="text-sm text-foreground/70">
                {stats.total_recommendation_runs} run
                {stats.total_recommendation_runs === 1 ? "" : "s"} so far
              </p>
            </div>
            {stats.top_compatibility_pct != null ? (
              <div className="text-right">
                <p className="text-3xl font-bold text-primary">{stats.top_compatibility_pct}%</p>
                <p className="text-xs text-foreground/70">compatibility</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <section aria-labelledby="metrics-heading" className="space-y-3">
        <h2 id="metrics-heading" className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Your profile
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metrics.map((metric) => (
            <Link key={metric.label} href={metric.href} className="group">
              <Card className="h-full transition-colors group-hover:border-primary/50">
                <CardContent className="flex items-center justify-between p-5">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">{metric.label}</p>
                    <p className="text-2xl font-bold">{metric.value}</p>
                  </div>
                  <metric.icon className="h-5 w-5 text-muted-foreground group-hover:text-primary" aria-hidden="true" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {progress ? (
        <section aria-labelledby="progress-heading" className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle id="progress-heading">Profile completeness</CardTitle>
              <CardDescription>
                {progress.completed_fields} of {progress.total_fields} steps complete
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={progress.score} aria-label={`Profile is ${progress.score}% complete`} />
              <p className="text-2xl font-bold">{progress.score}%</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next steps</CardTitle>
              <CardDescription>Each one moves the completeness score.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5">
                {progress.steps.map((step) => (
                  <li key={step.key}>
                    <Link
                      href={step.href}
                      className="flex items-start gap-2 rounded-md p-1.5 text-sm hover:bg-accent"
                    >
                      {step.completed ? (
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
                      ) : (
                        <Circle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      )}
                      <span className="min-w-0 flex-1">
                        <span className={step.completed ? "line-through text-muted-foreground" : "font-medium"}>
                          {step.label}
                        </span>
                        {!step.completed ? <span className="block text-xs text-muted-foreground">{step.hint}</span> : null}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </section>
      ) : null}

      <section aria-labelledby="ai-heading" className="space-y-3">
        <h2 id="ai-heading" className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          AI assistant
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {aiTools.map((tool) => (
            <Link key={tool.href} href={tool.href} className="group">
              <Card className="h-full transition-colors group-hover:border-primary/50">
                <CardContent className="space-y-1 p-5">
                  <tool.icon className="h-5 w-5 text-muted-foreground group-hover:text-primary" aria-hidden="true" />
                  <p className="pt-1 font-medium">{tool.label}</p>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
        {!aiEnabled ? (
          <p className="text-sm text-muted-foreground">
            The AI tools are not enabled on this deployment. Everything else on
            this page — the matching, the skill gap, the CV analysis — works
            without them.
          </p>
        ) : null}
      </section>
    </div>
  );
}
