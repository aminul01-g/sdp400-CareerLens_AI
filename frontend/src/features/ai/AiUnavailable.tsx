"use client";

/**
 * The panel shown when the AI layer is not available.
 *
 * The point of it is honesty. A deployment without a provider is not broken —
 * every other feature of CareerLens works — and a user who presses a button
 * and gets a stack trace learns nothing. This says what is missing, what
 * still works, and who to ask.
 */
import Link from "next/link";
import { Bot, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface AiUnavailableProps {
  /** What the user was trying to do, e.g. "ask the career mentor". */
  feature?: string;
  className?: string;
}

export function AiUnavailable({ feature, className }: AiUnavailableProps) {
  return (
    <Card className={`border-dashed ${className ?? ""}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bot className="h-4 w-4" aria-hidden="true" />
          The AI assistant is not enabled on this deployment
        </CardTitle>
        <CardDescription>
          {feature
            ? `You cannot ${feature} right now.`
            : "The AI features are not available right now."}{" "}
          Everything else in CareerLens — CV analysis, career matching and the
          skill-gap report — works exactly as before.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          The AI layer needs an API key for the model provider. An administrator
          can set <code className="font-mono text-xs">GROQ_API_KEY</code> in the
          deployment environment to turn it on. No other change is needed, and
          the application is designed to work without it.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" asChild>
            <Link href="/recommendations">Get recommendations</Link>
          </Button>
          <Button size="sm" variant="ghost" asChild>
            <Link href="/skill-gap">
              See your skill gap
              <ExternalLink className="ml-2 h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
