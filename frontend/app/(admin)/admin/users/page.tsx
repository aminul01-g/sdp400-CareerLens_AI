"use client";

/**
 * Registered accounts, with role control.
 *
 * Read-only apart from one action: promoting or demoting a role. That is the only
 * write in the whole admin surface that changes what a *person* can do rather
 * than what the *engine* matches against, which is why it gets its own page
 * instead of living under Job roles.
 *
 * Two things are deliberately not here. There is no delete: removing an account
 * is not implemented by the API, and inventing a soft-delete column here would
 * desynchronise the frontend from the schema. There is also no `user_id` on
 * feedback entries, so this page cannot link a person to what they wrote.
 *
 * Self-demotion is blocked. An admin who removes their own admin role is locked
 * out of every `/admin` route with no way back except a database edit, so the
 * control is disabled on your own row rather than left to fail server-side.
 */
import * as React from "react";
import { Loader2, Shield, Users } from "lucide-react";
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
import { useAuth } from "@/components/providers/AuthProvider";
import { errorMessage } from "@/lib/api/client";
import { useAdminUsers, useSetUserRole } from "@/lib/hooks/use-admin";
import type { UserRole } from "@/lib/api/types";

const PAGE_SIZE = 20;

const date = (value?: string | null) =>
  value ? new Date(value).toLocaleDateString() : "—";

export default function AdminUsersPage() {
  const [page, setPage] = React.useState(1);
  const { user: currentUser } = useAuth();
  const users = useAdminUsers(page);
  const setRole = useSetUserRole();
  const [notice, setNotice] = React.useState<string | null>(null);

  const items = users.data?.items ?? [];
  const total = users.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  async function changeRole(id: number, role: UserRole) {
    setNotice(null);
    try {
      await setRole.mutateAsync({ id, role });
    } catch (error) {
      setNotice(errorMessage(error, "We could not change that role."));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Every registered account. The role decides whether an account reaches this section at all."
      />

      {notice ? (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}

      {users.isPending ? (
        <Card>
          <CardContent className="p-4">
            <LoadingRows count={5} />
          </CardContent>
        </Card>
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Users className="h-8 w-8" aria-hidden="true" />}
          title="No accounts yet"
          description="Accounts appear here as soon as somebody registers."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Registered accounts and their roles</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Skills</TableHead>
                    <TableHead className="text-right">Projects</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead>Last seen</TableHead>
                    <TableHead className="w-40">Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((account) => {
                    const isSelf = account.id === currentUser?.id;
                    return (
                      <TableRow key={account.id}>
                        <TableCell className="font-medium">
                          {account.name}
                          {isSelf ? (
                            <Badge className="ml-2" variant="secondary">you</Badge>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{account.email}</TableCell>
                        <TableCell>
                          <Badge variant={account.is_active ? "default" : "secondary"}>
                            {account.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{account.skills_count}</TableCell>
                        <TableCell className="text-right tabular-nums">{account.projects_count}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {date(account.created_at)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {date(account.last_login_at)}
                        </TableCell>
                        <TableCell>
                          {isSelf ? (
                            <p className="text-xs text-muted-foreground">
                              Cannot change your own role.
                            </p>
                          ) : (
                            <Select
                              value={account.role}
                              onValueChange={(value) => void changeRole(account.id, value as UserRole)}
                              disabled={setRole.isPending}
                            >
                              <SelectTrigger aria-label={`Role for ${account.name}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="user">User</SelectItem>
                                <SelectItem value="admin">Admin</SelectItem>
                              </SelectContent>
                            </Select>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {total} account(s) total.
        </p>
        {pageCount > 1 ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {page} of {pageCount}
            </span>
            <button
              type="button"
              className="rounded-md border px-2.5 py-1.5 text-sm disabled:opacity-50"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || users.isFetching}
            >
              Previous
            </button>
            <button
              type="button"
              className="rounded-md border px-2.5 py-1.5 text-sm disabled:opacity-50"
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={page >= pageCount || users.isFetching}
            >
              Next
            </button>
          </div>
        ) : null}
      </div>

      {setRole.isPending ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Saving the role change…
        </p>
      ) : null}

      <Alert>
        <Shield className="h-4 w-4" aria-hidden="true" />
        <AlertDescription>
          The API is the enforcement point, not this page. Hiding a control here hides it from
          the UI only — every <code className="rounded bg-muted px-1 py-0.5 text-xs">/api/admin/*</code>{" "}
          route independently requires the <code className="rounded bg-muted px-1 py-0.5 text-xs">admin</code>{" "}
          role and answers <code className="rounded bg-muted px-1 py-0.5 text-xs">403</code> otherwise.
        </AlertDescription>
      </Alert>
    </div>
  );
}
