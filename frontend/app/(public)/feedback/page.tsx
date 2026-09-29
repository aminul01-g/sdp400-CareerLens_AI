"use client";

/** Feedback. Ported from the predecessor's `Feedback.tsx`, payload shape preserved. */
import * as React from "react";
import Link from "next/link";
import { Loader2, MessageSquare } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAuth } from "@/components/providers/AuthProvider";
import { feedbackApi } from "@/lib/api/feedback";
import { errorMessage } from "@/lib/api/client";
import { feedbackSchema } from "@/lib/schemas";

const CATEGORIES = ["general", "bug", "feature", "ui", "data", "other"] as const;

export default function FeedbackPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [category, setCategory] = React.useState<string>("general");
  const [message, setMessage] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [sent, setSent] = React.useState(false);
  const [isPending, setIsPending] = React.useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFieldErrors({});

    const parsed = feedbackSchema.safeParse({ category, message });
    if (!parsed.success) {
      setFieldErrors(Object.fromEntries(parsed.error.issues.map((i) => [String(i.path[0]), i.message])));
      return;
    }

    setIsPending(true);
    try {
      await feedbackApi.send({ category: parsed.data.category, message: parsed.data.message });
      setSent(true);
      setMessage("");
    } catch (err) {
      setError(errorMessage(err, "We could not send your feedback."));
    } finally {
      setIsPending(false);
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="h-8 w-48 animate-pulse rounded-md bg-muted" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-2xl space-y-8 px-4 py-12">
      <PageHeader
        title="Send feedback"
        description="Tell us what is working and what is not. Every submission is read."
      />

      {!isAuthenticated ? (
        <Alert>
          <AlertDescription>
            <Link href="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>{" "}
            to send feedback. Feedback requires an account so it can be attributed and followed
            up on.
          </AlertDescription>
        </Alert>
      ) : sent ? (
        <Alert role="status">
          <AlertDescription>Thank you — your feedback has been recorded.</AlertDescription>
        </Alert>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" aria-hidden="true" />
              Your feedback
            </CardTitle>
            <CardDescription>Bug reports, feature requests, or anything confusing.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {error ? (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((value) => (
                      <SelectItem key={value} value={value}>
                        {value}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="message">Message</Label>
                <Textarea
                  id="message"
                  rows={6}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="What happened, or what you would like to see?"
                  aria-invalid={Boolean(fieldErrors.message)}
                />
                {fieldErrors.message ? (
                  <p className="text-sm text-destructive">{fieldErrors.message}</p>
                ) : null}
              </div>

              <Button type="submit" disabled={isPending}>
                {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Send feedback
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
