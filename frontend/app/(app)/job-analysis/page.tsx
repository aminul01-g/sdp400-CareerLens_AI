"use client";

/**
 * The job-description analyser.
 *
 * The screen is built around one distinction the application insists on: a
 * skill the user does not have, against a skill the user never wrote down.
 * They look the same in a list of requirements and they are not the same
 * thing, so they are shown as three states and never collapsed into two.
 *
 * The compatibility figure is the application's own, computed over the skills
 * extracted from the description. It is not the official score for a
 * knowledge-base role, and the screen says so.
 */
import * as React from "react";
import { AlertCircle, CheckCircle2, FileSearch, HelpCircle, Loader2, XCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { AiToolsNav } from "@/features/ai/AiToolsNav";
import { AiUnavailable } from "@/features/ai/AiUnavailable";
import { StoredLanguageToggle, usePreferredLanguage } from "@/features/ai/LanguageToggle";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import { useAiStatus, useJobAnalysis } from "@/lib/hooks/use-ai";
import { useJobRoles } from "@/lib/hooks/use-jobs";
import type { AnalyzedRequirement, RequirementStatus } from "@/lib/api/types";

const STATUS_STYLE: Record<
  RequirementStatus,
  { label: string; icon: typeof CheckCircle2; className: string }
> = {
  met: {
    label: "On your profile",
    icon: CheckCircle2,
    className: "border-success/30 bg-success/10 text-success",
  },
  gap: {
    label: "Genuine gap",
    icon: XCircle,
    className: "border-destructive-surface/30 bg-destructive-surface/10 text-destructive",
  },
  no_evidence: {
    label: "Not on your profile",
    icon: HelpCircle,
    className: "border-border bg-muted text-muted-foreground",
  },
};

export default function JobAnalysisPage() {
  const status = useAiStatus();
  const roles = useJobRoles();
  const analyse = useJobAnalysis();

  const [description, setDescription] = React.useState("");
  const [roleId, setRoleId] = React.useState<number | null>(null);
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
    if (description.trim().length < 120 && roleId == null) {
      setFormError(
        "Paste a full job description, or choose a role from the knowledge base.",
      );
      return;
    }
    try {
      await analyse.mutateAsync({
        job_description: description,
        job_role_id: roleId ?? undefined,
        language,
      });
    } catch (caught) {
      setFormError(
        caught instanceof ApiError && caught.status === 503
          ? "The AI assistant is not enabled on this deployment."
          : errorMessage(caught, "The job description could not be analysed."),
      );
    }
  }

  if (status.isPending) {
    return <LoadingPage label="Checking the AI assistant" />;
  }

  const enabled = status.data?.enabled === true;
  const result = analyse.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Job analysis"
        description="Paste a job description and see which of its requirements you already meet, which are genuine gaps, and which your profile simply does not record."
        actions={<StoredLanguageToggle value={language} onChange={setLanguage} />}
      />

      <AiToolsNav />

      {!enabled ? (
        <AiUnavailable feature="analyse a job description" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileSearch className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                The job description
              </CardTitle>
              <CardDescription>
                Paste the description, or choose a role from the knowledge base
                to compare against. You can do both.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {formError ? (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-1.5">
                <Label htmlFor="job-description" className="text-sm font-medium">
                  Job description
                </Label>
                <Textarea
                  id="job-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={8}
                  placeholder="Paste the full description — the responsibilities, the required tools, the experience and the education it asks for."
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-sm font-medium">
                  Compare against a role from the knowledge base (optional)
                </Label>
                <Select
                  value={roleId != null ? String(roleId) : undefined}
                  onValueChange={(value) => setRoleId(Number(value))}
                >
                  <SelectTrigger aria-label="Choose a role to compare against">
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

              <Button onClick={() => void submit()} disabled={analyse.isPending}>
                {analyse.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <FileSearch className="mr-2 h-4 w-4" aria-hidden="true" />
                )}
                {analyse.isPending ? "Analysing…" : "Analyse the description"}
              </Button>
            </CardContent>
          </Card>

          {result ? (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{result.role_title}</CardTitle>
                  <CardDescription>{result.summary}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Coverage of the extracted requirements
                      </p>
                      <p className="text-3xl font-bold text-primary tabular-nums">
                        {result.coverage_pct.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">On your profile</p>
                      <p className="text-3xl font-bold tabular-nums">
                        {result.matched_count}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Genuine gaps</p>
                      <p className="text-3xl font-bold tabular-nums">
                        {result.gap_count}
                      </p>
                    </div>
                  </div>
                  <Progress value={result.coverage_pct} aria-label="Coverage" />
                  {result.official_compatibility_pct != null ? (
                    <p className="text-sm text-muted-foreground">
                      For the knowledge-base role you selected, the engine&apos;s
                      own compatibility score is{" "}
                      <span className="font-medium text-foreground tabular-nums">
                        {result.official_compatibility_pct.toFixed(1)}%
                      </span>
                      . The figure above is measured against the skills extracted
                      from the description you pasted, which is a different
                      calculation.
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      The figure above is measured against the skills extracted
                      from the description you pasted. It is not the
                      application&apos;s official score for a role.
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Requirements</CardTitle>
                  <CardDescription>
                    Each requirement is one of three things, and the difference
                    matters: a skill you have, a skill the role verifiably needs
                    and you do not have, and a skill your profile does not
                    record either way.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {result.requirements.map((requirement, index) => (
                    <RequirementRow
                      key={`${requirement.skill}-${index}`}
                      requirement={requirement}
                    />
                  ))}
                </CardContent>
              </Card>

              {result.checklist.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      What to do before you apply
                    </CardTitle>
                    <CardDescription>
                      In priority order. The ordering is the application&apos;s,
                      not the model&apos;s.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ol className="space-y-2">
                      {result.checklist.map((step, index) => (
                        <li key={index} className="flex gap-2 text-sm">
                          <span className="font-semibold text-muted-foreground tabular-nums">
                            {index + 1}.
                          </span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </CardContent>
                </Card>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                {result.tools_and_technologies.length > 0 ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Tools and technologies</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="flex flex-wrap gap-1.5">
                        {result.tools_and_technologies.map((item, index) => (
                          <li key={index}>
                            <Badge variant="secondary">{item}</Badge>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                ) : null}

                {result.responsibilities.length > 0 ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Responsibilities</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                        {result.responsibilities.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                ) : null}
              </div>

              {result.limitations.length > 0 ? (
                <Alert>
                  <AlertTitle className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" aria-hidden="true" />
                    What this description does not tell you
                  </AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc space-y-1 pl-5">
                      {result.limitations.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              ) : null}

              {result.unrecognised_skills.length > 0 ? (
                <Alert>
                  <AlertDescription>
                    These skills are not in the application&apos;s taxonomy, so
                    they could not be compared against your profile:{" "}
                    {result.unrecognised_skills.join(", ")}.
                  </AlertDescription>
                </Alert>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function RequirementRow({ requirement }: { requirement: AnalyzedRequirement }) {
  const style = STATUS_STYLE[requirement.status];
  const Icon = style.icon;
  return (
    <div className="rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${style.className}`}
        >
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          {style.label}
        </span>
        <span className="font-medium">
          {requirement.normalized_skill || requirement.skill}
        </span>
        {requirement.normalized_skill && requirement.normalized_skill !== requirement.skill ? (
          <span className="text-xs text-muted-foreground">
            (written as &quot;{requirement.skill}&quot;)
          </span>
        ) : null}
        <Badge variant="outline">{requirement.importance}</Badge>
        {requirement.proficiency != null ? (
          <Badge variant="secondary">proficiency {requirement.proficiency}/5</Badge>
        ) : null}
      </div>
      {requirement.evidence ? (
        <p className="mt-1 text-sm text-muted-foreground">
          &quot;{requirement.evidence}&quot;
        </p>
      ) : null}
      {requirement.note ? (
        <p className="mt-1 text-sm text-muted-foreground">{requirement.note}</p>
      ) : null}
    </div>
  );
}
