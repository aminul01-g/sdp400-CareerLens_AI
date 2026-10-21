"use client";

/**
 * The conversation surface for the career mentor.
 *
 * Two things it deliberately does not do:
 *
 * - It does not show a fake assistant message to fill the empty state. An
 *   empty conversation is an empty conversation, and a placeholder that looks
 *   like an answer teaches a user to trust a string they did not get from the
 *   model.
 * - It does not render generated text as HTML. The text arrives as a plain
 *   string and is rendered as a React child, so it is escaped by construction.
 */
import * as React from "react";
import { Bot, Loader2, Send, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { MentorAnswer, MentorTurn } from "@/lib/api/types";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  /** The assistant's answer, when the message came from the model. */
  answer?: MentorAnswer;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isPending?: boolean;
  /** Rendered above the conversation, e.g. the suggested prompts. */
  suggestions?: React.ReactNode;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function ChatPanel({
  messages,
  onSend,
  isPending = false,
  suggestions,
  placeholder = "Ask about your career, your skills, or what to learn next…",
  disabled = false,
  className,
}: ChatPanelProps) {
  const [draft, setDraft] = React.useState("");
  const listRef = React.useRef<HTMLDivElement | null>(null);
  const inputRef = React.useRef<HTMLTextAreaElement | null>(null);

  React.useEffect(() => {
    // Keep the newest turn in view as the conversation grows.
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages.length]);

  function submit() {
    const text = draft.trim();
    if (!text || isPending || disabled) return;
    onSend(text);
    setDraft("");
    inputRef.current?.focus();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div
        ref={listRef}
        className="max-h-[60vh] min-h-[16rem] space-y-4 overflow-y-auto rounded-lg border p-4"
        role="log"
        aria-label="Conversation"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Bot className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
            <p className="font-medium">Ask your career assistant a question</p>
            <p className="max-w-md text-sm text-muted-foreground">
              The answers are built from your own profile, your confirmed skills
              and your latest recommendation run. Where something is missing
              from your record, the assistant will say so rather than guess.
            </p>
          </div>
        ) : null}

        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              "flex gap-3",
              message.role === "user" ? "justify-end" : "justify-start",
            )}
          >
            {message.role === "assistant" ? (
              <span
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"
                aria-hidden="true"
              >
                <Bot className="h-4 w-4" />
              </span>
            ) : null}
            <div
              className={cn(
                "max-w-[85%] space-y-2 rounded-lg px-4 py-3 text-sm",
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-foreground",
              )}
            >
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
              {message.answer ? (
                <AnswerDetails answer={message.answer} />
              ) : null}
            </div>
            {message.role === "user" ? (
              <span
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
                aria-hidden="true"
              >
                <User className="h-4 w-4" />
              </span>
            ) : null}
          </div>
        ))}

        {isPending ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Thinking about your question…
          </div>
        ) : null}
      </div>

      {suggestions ? <div className="space-y-2">{suggestions}</div> : null}

      <div className="flex items-end gap-2">
        <Textarea
          ref={inputRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Your question"
          rows={2}
          disabled={disabled || isPending}
          className="min-h-[3rem] resize-y"
        />
        <Button
          type="button"
          onClick={submit}
          disabled={disabled || isPending || draft.trim().length === 0}
          aria-label="Send the question"
        >
          {isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="mr-2 h-4 w-4" aria-hidden="true" />
          )}
          Send
        </Button>
      </div>
    </div>
  );
}

function AnswerDetails({ answer }: { answer: MentorAnswer }) {
  return (
    <div className="space-y-2 border-t border-border/60 pt-2 text-xs text-muted-foreground">
      {answer.context_used.length > 0 ? (
        <p>
          <span className="font-medium text-foreground">Based on: </span>
          {answer.context_used.join("; ")}
        </p>
      ) : null}
      {answer.limitations.length > 0 ? (
        <div>
          <p className="font-medium text-foreground">What was missing from your record</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {answer.limitations.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export type { MentorTurn };
