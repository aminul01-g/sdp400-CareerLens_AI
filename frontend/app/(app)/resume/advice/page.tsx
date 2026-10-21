"use client";

/**
 * The CV improvement assistant.
 *
 * This screen *enhances* the CV analysis rather than replacing it. It reads
 * an analysed CV and produces a separate list of suggestions, which the user
 * reviews and applies themselves. The upload is never modified.
 *
 * The rules the screen enforces visibly: the suggestions are separated from
 * the original, the questions the user still needs to answer are shown
 * rather than filled in with a guess, and the disclaimer is on the page
 * rather than in a footnote.
 */
import * as React from "react";
import Link from "next/link";
import {
  FileText, HelpCircle, Loader2, ShieldAlert, Sparkles,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingPage } from "@/components/shared/Loading";
import { AiToolsNav } from "@/features/ai/AiToolsNav";
import { AiUnavailable } from "@/features/ai/AiUnavailable";
import { StoredLanguageToggle, usePreferredLanguage } from "@/features/ai/LanguageToggle";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import { useAiStatus, useCvAdvice } from "@/lib/hooks/use-ai";
import { useUploads } from "@/lib/hooks/use-cv";
import { useJobRoles } from "@/lib/hooks/use-jobs";

export default function CvAdvicePage() {
  const status = useAiStatus();
  const uploads = useUploads();
  const roles = useJobRoles();
  const advise = useCvAdvice();

  const [uploadId, setUploadId] = React.useState<number | null>(null);
  const [roleId, setRoleId] = React.useState<number | null>(null);
  const [includeCoverLetter, setIncludeCoverLetter] = React.useState(false);
  const [language, setLanguage] = React.useState<"en" | "bn">("en");
  const preferred = usePreferredLanguage();
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

  async function submit() {
    setFormError(null);
    if (uploadId == null) {
      setFormError("Choose an analysed CV first.");
      return;
    }
    try {
      await advise.mutateAsync({
        resume_upload_id: uploadId,
        job_role_id: roleId ?? undefined,
        include_cover_letter: includeCoverLetter,
        language,
      });
    } catch (caught) {
      setFormError(
        caught instanceof ApiError && caught.status === 503
          ? "The AI assistant is not enabled on this deployment."
          : errorMessage(caught, "The CV could not be reviewed."),
      );
    }
  }

  if (status.isPending) return <LoadingPage label="Checking the AI assistant" />;

  const enabled = status.data?.enabled === true;
  const result = advise.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="CV advice"
        description="Suggestions for presenting the CV you have already uploaded more clearly. Your CV is not changed — you decide what to keep."
        actions={<StoredLanguageToggle value={language} onChange={setLanguage} />}
      />

      <AiToolsNav />

      {!enabled ? (
        <AiUnavailable feature="review a CV" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Which CV should be reviewed
              </CardTitle>
              <CardDescription>
                Only CVs you have uploaded and analysed are listed.{" "}
                <Link
                  href="/resume"
                  className="font-medium text-primary underline-offset-4 hover:underline"
                >
                  Manage your CVs
                </Link>
                .
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {formError ? (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-1.5">
                <Label className="text-sm font-medium">Your analysed CV</Label>
                <Select
                  value={uploadId != null ? String(uploadId) : undefined}
                  onValueChange={(value) => setUploadId(Number(value))}
                >
                  <SelectTrigger aria-label="Choose a CV">
                    <SelectValue placeholder="Choose a CV" />
                  </SelectTrigger>
                  <SelectContent>
                    {(uploads.data?.items ?? []).map((upload) => (
                      <SelectItem key={upload.id} value={String(upload.id)}>
                        {upload.original_filename}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-sm font-medium">
                  Tailor the advice to a role (optional)
                </Label>
                <Select
                  value={roleId != null ? String(roleId) : undefined}
                  onValueChange={(value) => setRoleId(Number(value))}
                >
                  <SelectTrigger aria-label="Choose a target role">
                    <SelectValue placeholder="No role selected" />
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

              <div className="flex items-center gap-2">
                <Checkbox
                  id="cover-letter"
                  checked={includeCoverLetter}
                  onCheckedChange={(checked) => setIncludeCoverLetter(checked === true)}
                />
                <Label htmlFor="cover-letter" className="text-sm font-normal">
                  Also draft a cover letter for the selected role
                </Label>
              </div>

              <Button onClick={() => void submit()} disabled={advise.isPending}>
                {advise.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
                )}
                {advise.isPending ? "Reviewing your CV…" : "Review my CV"}
              </Button>
            </CardContent>
          </Card>

          {result ? (
            <div className="space-y-6">
              <Alert>
                <AlertTitle className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                  Read this before you use the suggestions
                </AlertTitle>
                <AlertDescription>{result.disclaimer}</AlertDescription>
              </Alert>

              {result.needs_information.length > 0 ? (
                <Alert>
                  <AlertTitle className="flex items-center gap-2">
                    <HelpCircle className="h-4 w-4" aria-hidden="true" />
                    What is still missing from your CV
                  </AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc space-y-1 pl-5">
                      {result.needs_information.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              ) : null}

              {result.professional_summary ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      A rewritten professional summary
                    </CardTitle>
                    <CardDescription>
                      Built only from what your CV and profile already say.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                      {result.professional_summary}
                    </p>
                  </CardContent>
                </Card>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <SuggestionCard
                  title="What your CV already communicates well"
                  items={result.effective_summary}
                />
                <SuggestionCard
                  title="Worth more emphasis"
                  items={result.emphasise}
                />
                <SuggestionCard
                  title="Clarity"
                  items={result.clarity_suggestions}
                />
                <SuggestionCard
                  title="Wording"
                  items={result.wording_suggestions}
                />
                <SuggestionCard
                  title="Describing your projects"
                  items={result.project_suggestions}
                />
                <SuggestionCard
                  title="For the role you selected"
                  items={result.job_specific_recommendations}
                  empty="No role was selected, so there is nothing role-specific to suggest yet."
                />
              </div>

              {result.bullet_points.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Draft bullet points
                    </CardTitle>
                    <CardDescription>
                      Each one is built from a fact already in your CV. Check
                      every one against the truth before you use it.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc space-y-1.5 pl-5 text-sm">
                      {result.bullet_points.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ) : null}

              {result.cover_letter ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Cover letter draft</CardTitle>
                    <CardDescription>
                      A draft to edit, not to send. It uses only what your CV
                      already says.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                      {result.cover_letter}
                    </p>
                  </CardContent>
                </Card>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function SuggestionCard({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {empty ?? "Nothing to suggest here."}
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {items.map((item, index) => (
              <li key={index} className="flex gap-2">
                <Badge variant="secondary" className="mt-0.5 h-5 shrink-0 px-1.5 text-[10px]">
                  {index + 1}
                </Badge>
                {item}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
