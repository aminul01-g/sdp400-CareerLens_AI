"use client";

/**
 * Feedback inbox.
 *
 * Read-only by design, and that is a backend decision rather than an omission:
 * `FeedbackRead` deliberately omits `user_id` ("an admin listing has no need for
 * it"). So an admin can read what was said and when, but not who said it. Adding
 * a sender column here would need the schema changed first, and quietly widening
 * a privacy-relevant read model to make a table look fuller is the wrong trade.
 *
 * The message is shown in full rather than truncated behind a dialog: the whole
 * point of an inbox is reading the text, and feedback is capped at 4,000
 * characters by the API, so there is nothing unbounded to defend against.
 */
import * as React from "react";
import { MessageSquare } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAdminFeedback } from "@/lib/hooks/use-admin";

/** The same set the API validates on write, mirrored for the badge colour. */
const CATEGORY_VARIANT: Record<string, "default" | "destructive" | "secondary" | "outline"> = {
  bug: "destructive",
  feature: "default",
  ui: "secondary",
  data: "secondary",
  general: "outline",
  other: "outline",
};

const timestamp = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

export default function AdminFeedbackPage() {
  const feedback = useAdminFeedback();
  const items = feedback.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feedback"
        description="What visitors sent from the public feedback form. Every submission is read."
      />

      {feedback.isPending ? (
        <Card>
          <CardContent className="p-4">
            <LoadingRows count={4} />
          </CardContent>
        </Card>
      ) : feedback.isError ? (
        <ErrorState error={feedback.error} onRetry={() => void feedback.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-8 w-8" aria-hidden="true" />}
          title="No feedback yet"
          description="Submissions from the public feedback form will appear here."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Feedback submissions</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-28">Category</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead className="w-20 text-right">Rating</TableHead>
                    <TableHead className="w-48">Received</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((entry) => (
                    <TableRow key={entry.id} className="align-top">
                      <TableCell>
                        <Badge variant={CATEGORY_VARIANT[entry.category] ?? "outline"}>
                          {entry.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-pre-wrap text-sm">{entry.message}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {entry.rating ?? "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {timestamp(entry.created_at)}
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
          This listing carries no sender. The API&apos;s read model omits{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">user_id</code> deliberately, so
          the inbox answers &ldquo;what was reported&rdquo; and not &ldquo;who reported it&rdquo;.
        </AlertDescription>
      </Alert>
    </div>
  );
}
