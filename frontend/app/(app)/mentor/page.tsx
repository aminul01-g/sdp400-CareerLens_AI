"use client";

/**
 * The AI career mentor.
 *
 * The conversation is held in the page rather than on the server. That is
 * deliberate: the server keeps only the last few turns when it calls the
 * provider, so a long chat does not grow the request, and a user's
 * transcript is not something the application needs to keep.
 *
 * The suggested prompts are derived from the user's own record — the top
 * match from their latest recommendation run, the role they are aiming at —
 * so they are questions this person can actually answer.
 */
import * as React from "react";
import Link from "next/link";
import { Lightbulb, MessageCircleQuestion, Sparkles } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { AiToolsNav } from "@/features/ai/AiToolsNav";
import { AiUnavailable } from "@/features/ai/AiUnavailable";
import { ChatPanel, type ChatMessage } from "@/features/ai/ChatPanel";
import { StoredLanguageToggle, usePreferredLanguage } from "@/features/ai/LanguageToggle";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import { useAskMentor, useAiStatus } from "@/lib/hooks/use-ai";
import { useRuns } from "@/lib/hooks/use-recommendations";

const GENERIC_PROMPTS = [
  "Which career path best matches my current skills, and why?",
  "Which missing skill should I prioritise first?",
  "What practical project would demonstrate my skills to employers?",
  "What should I do next to improve my career prospects?",
];

export default function MentorPage() {
  const status = useAiStatus();
  const [language, setLanguage] = React.useState<"en" | "bn">("en");
  const preferred = usePreferredLanguage();
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLanguage(preferred);
  }, [preferred]);

  const ask = useAskMentor();
  const runs = useRuns();

  const enabled = status.data?.enabled === true;

  const suggestions = React.useMemo(() => {
    const top = runs.data?.items?.[0];
    const prompts = [...GENERIC_PROMPTS];
    if (top?.top_role_title) {
      prompts.unshift(`Why does my top match look like ${top.top_role_title}?`);
    }
    return prompts;
  }, [runs.data]);

  async function send(message: string) {
    setError(null);
    const history = messages.map((item) => ({
      role: item.role,
      content: item.content,
    }));
    setMessages((previous) => [...previous, { role: "user", content: message }]);
    try {
      const answer = await ask.mutateAsync({ message, history, language });
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: answer.answer, answer },
      ]);
    } catch (caught) {
      // A provider failure must not leave the conversation pretending the
      // question was answered.
      setMessages((previous) => previous.slice(0, -1));
      setError(
        caught instanceof ApiError && caught.status === 503
          ? "The AI assistant is not available on this deployment."
          : errorMessage(caught, "The assistant could not answer that question."),
      );
    }
  }

  if (status.isPending) return <LoadingPage label="Checking the AI assistant" />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Career mentor"
        description="Ask about your career and get answers built from your own profile, your confirmed skills and your latest recommendation run."
        actions={
          <StoredLanguageToggle value={language} onChange={setLanguage} />
        }
      />

      <AiToolsNav />

      {!enabled ? (
        <AiUnavailable feature="ask the career mentor" />
      ) : (
        <>
          {error ? (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <ChatPanel
              messages={messages}
              onSend={(message) => void send(message)}
              isPending={ask.isPending}
              suggestions={
                messages.length === 0 ? (
                  <div className="space-y-2">
                    <p className="flex items-center gap-2 text-sm font-medium">
                      <Lightbulb className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                      Suggested questions
                    </p>
                    <ul className="flex flex-wrap gap-2">
                      {suggestions.map((prompt) => (
                        <li key={prompt}>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => void send(prompt)}
                            disabled={ask.isPending}
                          >
                            {prompt}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null
              }
            />

            <Card className="h-fit">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  What the answers use
                </CardTitle>
                <CardDescription>
                  The assistant is grounded in your own record, and says so when
                  something is missing from it.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <ul className="space-y-2">
                  <li className="flex gap-2">
                    <MessageCircleQuestion
                      className="mt-0.5 h-4 w-4 shrink-0"
                      aria-hidden="true"
                    />
                    Your confirmed skills, projects, education and work history.
                  </li>
                  <li className="flex gap-2">
                    <MessageCircleQuestion
                      className="mt-0.5 h-4 w-4 shrink-0"
                      aria-hidden="true"
                    />
                    The engine&apos;s own ranking and skill-gap report, read from
                    your latest run.
                  </li>
                </ul>
                <p>
                  The assistant never invents an employer, a credential, a
                  metric or a salary figure. If your record does not contain
                  what a question needs, it will ask you for it.
                </p>
                <p>
                  Want the plan rather than the conversation?{" "}
                  <Link
                    href="/roadmaps"
                    className="font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Generate a learning roadmap
                  </Link>
                  .
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
