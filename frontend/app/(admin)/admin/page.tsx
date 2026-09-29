"use client";

/**
 * Admin overview.
 *
 * Every figure is a real aggregate from `GET /api/admin/overview`. This replaces
 * the predecessor's dashboard, which displayed `totalUsers: "12,847"` and
 * `successRate: "94%"` — numbers with no relationship to anything.
 */
import Link from "next/link";
import { Activity, Briefcase, Cpu, Database, GraduationCap, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAdminOverview } from "@/lib/hooks/use-admin";

export default function AdminOverviewPage() {
  const overview = useAdminOverview();

  if (overview.isPending) return <LoadingPage label="Loading the admin overview" />;
  if (overview.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Admin" />
        <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />
      </div>
    );
  }

  const data = overview.data;

  const stats = [
    { label: "Job roles", value: data.role_count, hint: `${data.active_role_count} active`, icon: Briefcase, href: "/admin/jobs" },
    { label: "Taxonomy skills", value: data.skill_count, hint: `${data.alias_count} aliases`, icon: Cpu },
    { label: "Users", value: data.user_count, hint: "registered accounts", icon: Users },
    { label: "Recommendation runs", value: data.recommendation_run_count, hint: data.latest_run_at ? `last ${new Date(data.latest_run_at).toLocaleDateString()}` : "none yet", icon: Activity },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin"
        description="The knowledge base the recommendation engine matches against. Everything here is a real count."
        actions={<Button asChild><Link href="/admin/jobs">Manage job roles</Link></Button>}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <stat.icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              </div>
              <p className="mt-1 text-3xl font-bold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Roles by family</CardTitle>
            <CardDescription>Active roles only</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.families.map((family) => (
                <li key={family.family} className="flex items-center justify-between gap-3 text-sm">
                  <span>{family.family}</span>
                  <span className="flex items-center gap-2">
                    <div className="h-1.5 w-24 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary"
                        style={{ width: `${(family.count / Math.max(...data.families.map((f) => f.count))) * 100}%` }}
                      />
                    </div>
                    <span className="w-6 text-right tabular-nums">{family.count}</span>
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most required skills</CardTitle>
            <CardDescription>How many job roles list each skill</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.top_skills.map((skill) => (
                <li key={skill.skill_id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate">{skill.name}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Badge variant="outline">{skill.category}</Badge>
                    <span className="w-6 text-right tabular-nums">{skill.role_count}</span>
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button asChild variant="outline">
          <Link href="/admin/evaluation">
            <GraduationCap className="mr-2 h-4 w-4" aria-hidden="true" />
            Evaluation report
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/admin/jobs">
            <Database className="mr-2 h-4 w-4" aria-hidden="true" />
            Knowledge base
          </Link>
        </Button>
      </div>
    </div>
  );
}
