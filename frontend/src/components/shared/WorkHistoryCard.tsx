"use client";

/**
 * The work history.
 *
 * The experience signal is what makes a junior and a principal with the same
 * declared skills score differently. This card is where that signal comes
 * from: rows the user typed, and rows the CV pipeline proposed.
 *
 * A proposed row is shown differently from a confirmed one, and it has to be
 * accepted explicitly. The same rule the detected skills follow: the system
 * proposes, the user disposes.
 */
import * as React from "react";
import { Briefcase, Check, Loader2, Plus, Trash2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api/client";
import {
  useAddWorkHistory,
  useConfirmWorkHistory,
  useDeleteWorkHistory,
  useWorkHistory,
} from "@/lib/hooks/use-work-history";

const formatMonth = (value: string | null): string => {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short" });
};

export function WorkHistoryCard() {
  const history = useWorkHistory();
  const add = useAddWorkHistory();
  const confirm = useConfirmWorkHistory();
  const remove = useDeleteWorkHistory();

  const [employer, setEmployer] = React.useState("");
  const [title, setTitle] = React.useState("");
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const [notice, setNotice] = React.useState<string | null>(null);

  const entries = history.data ?? [];
  const proposed = entries.filter((entry) => !entry.confirmed);
  const confirmed = entries.filter((entry) => entry.confirmed);

  async function handleAdd(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    try {
      await add.mutateAsync({
        employer: employer.trim(),
        title: title.trim() || null,
        start_date: start || null,
        end_date: end || null,
      });
      setEmployer("");
      setTitle("");
      setStart("");
      setEnd("");
    } catch (error) {
      setNotice(errorMessage(error, "We could not add that role."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5" aria-hidden="true" />
          Work history
        </CardTitle>
        <CardDescription>
          Where you have worked, and for how long. This is what the engine uses to
          judge your level, so it is worth filling in. Overlapping roles count once.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {notice ? (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        ) : null}

        {history.isPending ? (
          <p className="text-sm text-muted-foreground" role="status">
            <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
            Loading your work history…
          </p>
        ) : null}

        {proposed.length > 0 ? (
          <div className="space-y-2">
            <p className="text-sm font-medium">Read from your CV — confirm what is right</p>
            <ul className="divide-y rounded-md border border-dashed">
              {proposed.map((entry) => (
                <li key={entry.id} className="flex flex-wrap items-center gap-3 p-3 text-sm">
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{entry.employer}</span>
                    <span className="block text-xs text-muted-foreground">
                      {[formatMonth(entry.start_date), formatMonth(entry.end_date)]
                        .filter(Boolean)
                        .join(" – ") || "No dates found"}
                    </span>
                  </span>
                  <Badge variant="outline">Not confirmed</Badge>
                  <Button
                    size="sm"
                    disabled={confirm.isPending}
                    onClick={() => void confirm.mutateAsync(entry.id)}
                  >
                    <Check className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                    Confirm
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove the proposed role at ${entry.employer}`}
                    onClick={() => void remove.mutateAsync(entry.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {confirmed.length > 0 ? (
          <ul className="divide-y rounded-md border">
            {confirmed.map((entry) => (
              <li key={entry.id} className="flex flex-wrap items-center gap-3 p-3 text-sm">
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{entry.employer}</span>
                  <span className="block text-xs text-muted-foreground">
                    {[entry.title, [formatMonth(entry.start_date), formatMonth(entry.end_date)]
                      .filter(Boolean)
                      .join(" – ")]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
                {entry.source === "cv_extracted" ? (
                  <Badge variant="secondary">From your CV</Badge>
                ) : null}
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${entry.employer} from your work history`}
                  onClick={() => void remove.mutateAsync(entry.id)}
                >
                  <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        ) : null}

        {entries.length === 0 && !history.isPending ? (
          <p className="text-sm text-muted-foreground">
            Nothing yet. Add a role below, or upload a CV and we will read the dates
            out of it for you to confirm.
          </p>
        ) : null}

        <form onSubmit={handleAdd} className="space-y-3 border-t pt-4">
          <p className="text-sm font-medium">Add a role</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="wh-employer" className="text-xs">
                Employer
              </Label>
              <Input
                id="wh-employer"
                value={employer}
                onChange={(event) => setEmployer(event.target.value)}
                placeholder="Acme Analytics"
                maxLength={160}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="wh-title" className="text-xs">
                Job title
              </Label>
              <Input
                id="wh-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Data Scientist"
                maxLength={160}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="wh-start" className="text-xs">
                From
              </Label>
              <Input
                id="wh-start"
                type="date"
                value={start}
                onChange={(event) => setStart(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="wh-end" className="text-xs">
                To
              </Label>
              <Input
                id="wh-end"
                type="date"
                value={end}
                onChange={(event) => setEnd(event.target.value)}
                aria-describedby="wh-end-hint"
              />
              <p id="wh-end-hint" className="text-xs text-muted-foreground">
                Leave blank if you are still there.
              </p>
            </div>
          </div>
          <Button type="submit" variant="outline" disabled={add.isPending || !employer.trim()}>
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Add this role
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
