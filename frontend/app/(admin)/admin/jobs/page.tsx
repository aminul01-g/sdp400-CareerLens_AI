"use client";

/**
 * Job role management.
 *
 * A product surface, not a database browser: roles are listed with the numbers an
 * administrator actually needs (required-skill count, total weight, active state),
 * and every write goes through validation rather than around it.
 *
 * This replaces Flask-Admin, which rendered a raw column grid over six models —
 * including `user.password_hash` — to anonymous visitors.
 */
import * as React from "react";
import Link from "next/link";
import { Plus, Search, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAdminJobs, useJobFamilies } from "@/lib/hooks/use-admin-families";
import { JobRoleForm } from "@/features/admin/JobRoleForm";

export default function AdminJobsPage() {
  const [query, setQuery] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [family, setFamily] = React.useState("all");
  const [isActive, setIsActive] = React.useState("all");
  const [creating, setCreating] = React.useState(false);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const families = useJobFamilies();
  const jobs = useAdminJobs({
    q: debounced || undefined,
    family: family === "all" ? undefined : family,
    is_active: isActive === "all" ? undefined : isActive === "true",
  });

  if (jobs.isPending) {
    return <div className="space-y-6"><PageHeader title="Job roles" description="Loading…" /><LoadingRows count={6} /></div>;
  }
  if (jobs.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Job roles" />
        <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
      </div>
    );
  }

  const items = jobs.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Job roles"
        description="The knowledge base the engine scores users against. Each role carries a description and a weighted set of required skills."
        actions={<Button onClick={() => setCreating(true)}><Plus className="mr-2 h-4 w-4" aria-hidden="true" />New job role</Button>}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-2 sm:col-span-1">
          <Label htmlFor="role-search" className="sr-only">Search roles</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input
              id="role-search" value={query} onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title or description" className="pl-8"
            />
          </div>
        </div>
        <Select value={family} onValueChange={setFamily}>
          <SelectTrigger aria-label="Filter by role family">
            <SelectValue placeholder="All families" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All families</SelectItem>
            {(families.data ?? []).map((f) => (
              <SelectItem key={f.family} value={f.family}>{f.family} ({f.count})</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={isActive} onValueChange={setIsActive}>
          <SelectTrigger aria-label="Filter by seniority">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Active and inactive</SelectItem>
            <SelectItem value="true">Active only</SelectItem>
            <SelectItem value="false">Inactive only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={<Shield className="h-8 w-8" aria-hidden="true" />}
          title="No job roles match"
          description="Adjust the filters, or create the first role in the knowledge base."
          action={{ label: "Create a job role", onClick: () => setCreating(true) }}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Job roles in the knowledge base</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Family</TableHead>
                    <TableHead>Seniority</TableHead>
                    <TableHead className="text-right">Skills</TableHead>
                    <TableHead className="text-right">Total weight</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell>
                        <Link href={`/admin/jobs/${role.id}`} className="font-medium text-primary hover:underline">
                          {role.title}
                        </Link>
                        <p className="max-w-md truncate text-xs text-muted-foreground">{role.description}</p>
                      </TableCell>
                      <TableCell>{role.family}</TableCell>
                      <TableCell>{role.seniority ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{role.required_skills_count}</TableCell>
                      <TableCell className="text-right tabular-nums">{Number(role.total_weight).toFixed(2)}</TableCell>
                      <TableCell>
                        <Badge variant={role.is_active ? "default" : "secondary"}>
                          {role.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-sm text-muted-foreground">{jobs.data?.total ?? 0} role(s) total.</p>

      <JobRoleForm open={creating} onOpenChange={setCreating} />
    </div>
  );
}
