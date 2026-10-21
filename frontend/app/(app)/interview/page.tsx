"use client";

/**
 * The mock interview simulator.
 *
 * The screen is careful about one number. The practice score is computed by
 * the application from five rubric dimensions, and it is labelled as a
 * practice score everywhere it appears — never as a prediction of hiring.
 * The rubric itself is shown, so the number is never a bare figure the user
 * has to take on trust.
 */
import * as React from "react";
import Link from "next/link";
import {
  ClipboardList, History, Loader2, MessageSquareText, Send, Trash2,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
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
import {
  useAiStatus, useDeleteInterview, useInterview, useInterviews, useNextQuestion,
  useStartInterview, useSubmitAnswer,
} from "@/lib/hooks/use-ai";
import { useJobRoles } from "@/lib/hooks/use-jobs";
import type { InterviewExchange } from "@/lib/api/types";

const CATEGORY_LABEL: Record<string, string> = {
  technical: "Technical",
  problem_solving: "Problem solving",
  project: "Project",
  behavioral: "Behavioural",
  scenario: "Scenario",
  follow_up: "Follow-up",
};

export default function InterviewPage() {
  const status = useAiStatus();
  const roles = useJobRoles();
  const sessions = useInterviews();
  const start = useStartInterview();

  const [roleId, setRoleId] = React.useState<number | null>(null);
  const [language, setLanguage] = React.useState<"en" | "bn">("en");
  const preferred = usePreferredLanguage();
  const [sessionId, setSessionId] = React.useState<number | null>(null);
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

  async function begin() {
    setFormError(null);
    if (roleId == null) {
      setFormError("Choose a role first.");
      return;
    }
    try {
      const session = await start.mutateAsync({
        job_role_id: roleId,
        language,
        question_count: 5,
      });
      setSessionId(session.id);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError && caught.status === 503
          ? "The AI assistant is not enabled on this deployment."
          : errorMessage(caught, "The interview could not be prepared."),
      );
    }
  }

  if (status.isPending) return <LoadingPage label="Checking the AI assistant" />;

  const enabled = status.data?.enabled === true;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mock interview"
        description="Practise against a real role, get structured feedback on each answer, and see exactly which rubric dimension your score came from."
        actions={<StoredLanguageToggle value={language} onChange={setLanguage} />}
      />

      <AiToolsNav />

      {!enabled ? (
        <AiUnavailable feature="run a mock interview" />
      ) : (
        <>
          {sessionId == null ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ClipboardList className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    Start an interview
                  </CardTitle>
                  <CardDescription>
                    The questions are drawn from the role&apos;s requirements and
                    from your own experience, so they are answerable rather than
                    generic.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {formError ? (
                    <Alert variant="destructive" role="alert">
                      <AlertDescription>{formError}</AlertDescription>
                    </Alert>
                  ) : null}
                  <div className="space-y-1.5">
                    <Label className="text-sm font-medium">Role</Label>
                    <Select
                      value={roleId != null ? String(roleId) : undefined}
                      onValueChange={(value) => setRoleId(Number(value))}
                    >
                      <SelectTrigger aria-label="Choose a role">
                        <SelectValue placeholder="Choose a role" />
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
                  <Button onClick={() => void begin()} disabled={start.isPending}>
                    {start.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <ClipboardList className="mr-2 h-4 w-4" aria-hidden="true" />
                    )}
                    {start.isPending ? "Preparing questions…" : "Start the interview"}
                  </Button>
                </CardContent>
              </Card>

              <SessionHistory
                sessions={sessions.data?.items ?? []}
                isPending={sessions.isPending}
                isError={sessions.isError}
                error={sessions.error}
                onRetry={() => void sessions.refetch()}
              />
            </>
          ) : (
            <SessionRunner sessionId={sessionId} onClose={() => setSessionId(null)} />
          )}
        </>
      )}
    </div>
  );
}

function SessionHistory({
  sessions,
  isPending,
  isError,
  error,
  onRetry,
}: {
  sessions: import("@/lib/api/types").InterviewSessionSummary[];
  isPending: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const remove = useDeleteInterview();
  const [confirming, setConfirming] = React.useState<number | null>(null);

  if (isPending) return <LoadingPage label="Loading your interview history" />;
  if (isError) return <ErrorState error={error} onRetry={onRetry} />;
  if (sessions.length === 0) {
    return (
      <EmptyState
        icon={<History className="h-8 w-8" aria-hidden="true" />}
        title="No interviews yet"
        description="Start one above. Every session is saved with its questions, your answers and the feedback, so you can read it again later."
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Your previous interviews
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
            >
              <div className="min-w-0 space-y-1">
                <p className="font-medium">{session.job_label}</p>
                <p className="text-sm text-muted-foreground">
                  {new Date(session.created_at).toLocaleDateString()} ·{" "}
                  {session.answered_count} of {session.question_count} answered
                  {session.average_practice_score != null
                    ? ` · practice score ${session.average_practice_score}/${25}`
                    : ""}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/interview?session=${session.id}`}>Open</Link>
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setConfirming(session.id)}
                  aria-label={`Delete the ${session.job_label} interview`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
        {confirming != null ? (
          <Alert className="mt-3">
            <AlertDescription className="flex flex-wrap items-center gap-2">
              Delete this interview and its feedback?
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  void remove.mutateAsync(confirming);
                  setConfirming(null);
                }}
              >
                Delete
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>
                Keep it
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

function SessionRunner({
  sessionId,
  onClose,
}: {
  sessionId: number;
  onClose: () => void;
}) {
  const session = useInterview(sessionId);
  const submit = useSubmitAnswer();
  const next = useNextQuestion();

  const [draft, setDraft] = React.useState("");
  const [activePosition, setActivePosition] = React.useState<number | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  if (session.isPending) return <LoadingPage label="Loading the interview" />;
  if (session.isError) {
    return <ErrorState error={session.error} onRetry={() => void session.refetch()} />;
  }
  const data = session.data;
  if (!data) return null;

  const exchanges = data.exchanges;
  const current =
    exchanges.find((item) => item.position === activePosition) ??
    exchanges.find((item) => !item.answer) ??
    exchanges[0];

  async function sendAnswer() {
    if (!current) return;
    const text = draft.trim();
    if (!text) return;
    setError(null);
    try {
      await submit.mutateAsync({
        sessionId,
        answer: text,
        position: current.position,
      });
      setDraft("");
    } catch (caught) {
      setError(errorMessage(caught, "The answer could not be assessed."));
    }
  }

  async function askFollowUp() {
    setError(null);
    try {
      await next.mutateAsync(sessionId);
    } catch (caught) {
      setError(errorMessage(caught, "The follow-up question could not be produced."));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium">{data.job_label}</p>
          <p className="text-sm text-muted-foreground">
            {exchanges.filter((item) => item.answer).length} of {exchanges.length}{" "}
            answered
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onClose}>
          Finish and go back
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-4">
          {current ? (
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    {CATEGORY_LABEL[current.question.category] ??
                      current.question.category}
                  </Badge>
                  <Badge variant="outline">{current.question.difficulty}</Badge>
                  <span className="text-sm text-muted-foreground">
                    Question {current.position} of {exchanges.length}
                  </span>
                </div>
                <CardTitle className="text-base leading-relaxed">
                  {current.question.question}
                </CardTitle>
                {current.question.focus ? (
                  <CardDescription>{current.question.focus}</CardDescription>
                ) : null}
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="interview-answer" className="text-sm font-medium">
                    Your answer
                  </Label>
                  <Textarea
                    id="interview-answer"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    rows={6}
                    placeholder="Answer as you would in the interview — what you would do, and why."
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void sendAnswer()} disabled={submit.isPending}>
                    {submit.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Send className="mr-2 h-4 w-4" aria-hidden="true" />
                    )}
                    Submit the answer
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void askFollowUp()}
                    disabled={next.isPending}
                  >
                    {next.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <MessageSquareText className="mr-2 h-4 w-4" aria-hidden="true" />
                    )}
                    Ask me a follow-up
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {current?.feedback ? (
            <FeedbackCard exchange={current} />
          ) : null}
        </div>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {exchanges.map((item) => (
                <li key={item.position}>
                  <button
                    type="button"
                    onClick={() => setActivePosition(item.position)}
                    className={`w-full rounded-md border px-2.5 py-2 text-left text-sm transition-colors ${
                      item.position === current?.position
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted"
                    }`}
                    aria-current={
                      item.position === current?.position ? "true" : undefined
                    }
                  >
                    <span className="block font-medium">
                      {item.position}. {CATEGORY_LABEL[item.question.category]}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {item.answer ? "Answered" : "Not answered yet"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function FeedbackCard({ exchange }: { exchange: InterviewExchange }) {
  const feedback = exchange.feedback;
  if (!feedback) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Feedback</CardTitle>
        <CardDescription>{feedback.score_note}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Practice score</p>
            <p className="text-2xl font-bold text-primary tabular-nums">
              {feedback.practice_score}
              <span className="text-base font-medium text-muted-foreground">
                /{feedback.max_practice_score}
              </span>
            </p>
          </div>
          <Progress
            value={
              feedback.max_practice_score > 0
                ? (feedback.practice_score / feedback.max_practice_score) * 100
                : 0
            }
            className="mt-2"
            aria-label="Practice score"
          />
        </div>

        <div>
          <p className="text-sm font-medium">The rubric</p>
          <ul className="mt-2 space-y-2">
            {feedback.dimensions.map((dimension) => (
              <li key={dimension.key} className="rounded-md border p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{dimension.label}</span>
                  <span className="text-sm tabular-nums text-muted-foreground">
                    {dimension.score}/{dimension.max_score}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {dimension.description}
                </p>
                {dimension.note ? (
                  <p className="mt-1 text-sm">{dimension.note}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>

        <FeedbackList title="What you did well" items={feedback.strengths} />
        <FeedbackList title="What the answer missed" items={feedback.missed_points} />
        <FeedbackList
          title="Technical inaccuracies"
          items={feedback.technical_inaccuracies}
          empty="None identified."
        />
        <FeedbackList
          title="How to make it clearer"
          items={feedback.clarity_improvements}
        />
        <FeedbackList
          title="Practise next"
          items={feedback.further_practice}
        />

        {feedback.example_answer ? (
          <div>
            <p className="text-sm font-medium">A stronger answer</p>
            <p className="mt-1 whitespace-pre-wrap rounded-md bg-muted p-3 text-sm">
              {feedback.example_answer}
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function FeedbackList({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty?: string;
}) {
  if (items.length === 0 && !empty) return null;
  return (
    <div>
      <p className="text-sm font-medium">{title}</p>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
