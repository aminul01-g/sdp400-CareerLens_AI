"use client";

/**
 * The audit trail.
 *
 * Who changed what, when, and from where. The rows are written in the same
 * transaction as the change they describe, so this table cannot disagree with
 * the data it describes — which is the only property that makes an audit log
 * worth reading.
 *
 * `action` and `entity_type` are the stable identifiers, and they are what the
 * filters use. `summary` is prose, and it may be reworded at any time.
 */
import * as React from "react";
import { ScrollText } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAdminAudit } from "@/lib/hooks/use-admin";

const ACTION_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All actions" },
  { value: "auth.login_succeeded", label: "Sign-ins" },
  { value: "auth.login_failed", label: "Failed sign-ins" },
  { value: "auth.registered", label: "Registrations" },
  { value: "auth.password_changed", label: "Password changes" },
  { value: "user.role_changed", label: "Role changes" },
  { value: "job_role.created", label: "Roles created" },
  { value: "job_role.updated", label: "Roles edited" },
  { value: "job_role.deleted", label: "Roles deleted" },
  { value: "job_role.skills_replaced", label: "Role skill sets replaced" },
  { value: "taxonomy.skill_created", label: "Taxonomy entries added" },
  { value: "taxonomy.skill_updated", label: "Taxonomy entries edited" },
  { value: "taxonomy.skill_deleted", label: "Taxonomy entries removed" },
];

const timestamp = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

export default function AdminAuditPage() {
  const [action, setAction] = React.useState("all");
  const audit = useAdminAudit({ action: action === "all" ? undefined : action });
  const items = audit.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit log"
        description="Every administrative change, and every sign-in, recorded as it happened."
        actions={
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger className="w-56" aria-label="Filter by action">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACTION_FILTERS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {audit.isPending ? (
        <Card>
          <CardContent className="p-4">
            <LoadingRows count={5} />
          </CardContent>
        </Card>
      ) : audit.isError ? (
        <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ScrollText className="h-8 w-8" aria-hidden="true" />}
          title="Nothing recorded yet"
          description="Administrative changes and sign-in events will appear here as they happen."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Audit trail</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-44">When</TableHead>
                    <TableHead className="w-48">Actor</TableHead>
                    <TableHead className="w-56">Action</TableHead>
                    <TableHead>What happened</TableHead>
                    <TableHead className="w-40">From</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((entry) => (
                    <TableRow key={entry.id} className="align-top">
                      <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                        {timestamp(entry.created_at)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {entry.actor_email ?? <span className="text-muted-foreground">anonymous</span>}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono text-xs">
                          {entry.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {entry.summary}
                        {entry.entity_id ? (
                          <span className="block text-xs text-muted-foreground">
                            {entry.entity_type} #{entry.entity_id}
                          </span>
                        ) : null}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {entry.client_ip ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <Alert>
        <AlertDescription>
          The actor is kept even after the account is deleted: the row survives its
          author, so a record of what happened cannot be erased by removing the
          person who did it.
        </AlertDescription>
      </Alert>
    </div>
  );
}
