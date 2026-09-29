"use client";

/**
 * CV upload and detected-skill confirmation.
 *
 * The confirmation step is the point of this screen. Detected skills are *staged*;
 * nothing reaches the user's profile until they accept it, which is what makes
 * "every skill in the profile is user-confirmed" a real invariant rather than a
 * UI convention. The panel is therefore titled "Confirm your skills" and its
 * primary action says how many skills it will add.
 *
 * The four failure modes each get distinct copy, because each needs a different
 * user action:
 *   415 wrong type     -> upload a PDF or DOCX
 *   413 too large     -> upload something under 5 MB
 *   422 scanned PDF   -> upload a text-based file, or add skills manually
 *   500 extraction    -> try again, or add skills manually
 */
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2, FileText, Loader2, Trash2, Upload, X,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import type { DetectedSkill, UploadResponse } from "@/lib/api/types";
import { useConfirmSkills } from "@/lib/hooks/use-skills";
import { useDeleteUpload, useUploadCv, useUploads } from "@/lib/hooks/use-cv";

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPT = ".pdf,.docx";

interface Selection {
  accepted: boolean;
  proficiency: number;
}

export default function ResumePage() {
  const router = useRouter();
  const uploads = useUploads();
  const uploadCv = useUploadCv();
  const deleteUpload = useDeleteUpload();
  const confirmSkills = useConfirmSkills();

  const [file, setFile] = React.useState<File | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [progress, setProgress] = React.useState<number | null>(null);
  const [uploadError, setUploadError] = React.useState<{ message: string; code: string } | null>(null);
  const [result, setResult] = React.useState<UploadResponse | null>(null);
  const [selections, setSelections] = React.useState<Record<number, Selection>>({});
  const [pendingRemoval, setPendingRemoval] = React.useState<number | null>(null);
  const [confirmed, setConfirmed] = React.useState<string | null>(null);

  function validate(candidate: File): string | null {
    const extension = candidate.name.slice(candidate.name.lastIndexOf(".")).toLowerCase();
    if (![".pdf", ".docx"].includes(extension)) {
      return "That file type is not supported. Upload a PDF or DOCX file.";
    }
    if (candidate.size > MAX_BYTES) {
      return `That file is ${(candidate.size / 1024 / 1024).toFixed(1)} MB. The limit is 5 MB.`;
    }
    if (candidate.size === 0) return "That file is empty.";
    return null;
  }

  async function startUpload(candidate: File) {
    const problem = validate(candidate);
    if (problem) {
      setUploadError({ message: problem, code: "client_validation" });
      setFile(null);
      return;
    }
    setFile(candidate);
    setUploadError(null);
    setResult(null);
    setConfirmed(null);
    setProgress(0);
    try {
      const response = await uploadCv.mutateAsync({ file: candidate, onProgress: setProgress });
      setResult(response);
      // Default to accepting everything: the user is confirming, not hunting.
      setSelections(
        Object.fromEntries(
          response.detected_skills.map((skill) => [skill.skill_id, { accepted: true, proficiency: 3 }]),
        ),
      );
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "upload_failed";
      setUploadError({ message: errorMessage(error, "The upload failed."), code });
      setFile(null);
    } finally {
      setProgress(null);
    }
  }

  async function handleConfirm() {
    if (!result) return;
    const payload = Object.entries(selections).map(([skillId, selection]) => ({
      skill_id: Number(skillId),
      accepted: selection.accepted,
      proficiency: selection.accepted ? selection.proficiency : undefined,
    }));
    try {
      const outcome = await confirmSkills.mutateAsync({
        resume_upload_id: result.resume_upload_id,
        skills: payload,
      });
      setConfirmed(
        `Added ${outcome.added} skill${outcome.added === 1 ? "" : "s"}` +
          (outcome.updated ? `, updated ${outcome.updated}` : "") +
          (outcome.declined ? `, declined ${outcome.declined}` : "") +
          (outcome.rejected.length ? `, ${outcome.rejected.length} could not be matched` : "") +
          ".",
      );
    } catch (error) {
      setUploadError({ message: errorMessage(error, "We could not save your choices."), code: "confirm_failed" });
    }
  }

  const acceptedCount = result
    ? result.detected_skills.filter((s) => selections[s.skill_id]?.accepted).length
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Resume analysis"
        description="Upload a CV and we will extract its text and detect which taxonomy skills it mentions. You confirm the result before anything is added to your profile."
      />

      <Alert>
        <AlertTitle>Scanned PDFs cannot be read</AlertTitle>
        <AlertDescription>
          We do not perform OCR, so an image-only PDF has no text to analyse. If your CV is a
          scan, upload a text-based PDF or a DOCX file — or{" "}
          <Link href="/skills" className="font-medium text-primary hover:underline">
            add your skills manually
          </Link>
          , which works identically.
        </AlertDescription>
      </Alert>

      {uploadError ? (
        <Alert variant="destructive" role="alert">
          <AlertTitle>
            {uploadError.code === "ocr_not_supported"
              ? "This looks like a scanned document"
              : uploadError.code === "payload_too_large"
                ? "That file is too large"
                : uploadError.code === "unsupported_media_type"
                  ? "Unsupported file type"
                  : "The upload did not work"}
          </AlertTitle>
          <AlertDescription className="flex items-start justify-between gap-3">
            {uploadError.message}
            <Button variant="ghost" size="sm" onClick={() => setUploadError(null)}>
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Upload your CV</CardTitle>
          <CardDescription>PDF or DOCX, at most 5 MB.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const dropped = event.dataTransfer.files?.[0];
              if (dropped) void startUpload(dropped);
            }}
            className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors ${
              dragging ? "border-primary bg-primary/5" : "border-muted-foreground/30"
            }`}
          >
            <Upload className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-medium">Drag a file here, or choose one</p>
              <p className="text-sm text-muted-foreground">
                Your file is processed to extract text and detect skills. Nothing is saved to
                your profile until you confirm it.
              </p>
            </div>
            <label className="cursor-pointer">
              <span className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
                Choose a file
              </span>
              <input
                type="file"
                accept={ACCEPT}
                className="sr-only"
                onChange={(event) => {
                  const chosen = event.target.files?.[0];
                  if (chosen) void startUpload(chosen);
                }}
              />
            </label>
          </div>

          {uploadCv.isPending ? (
            <div className="space-y-2">
              <Progress value={progress ?? 0} aria-label="Upload progress" />
              <p className="text-sm text-muted-foreground" role="status">
                {progress !== null && progress < 100
                  ? `Uploading ${file?.name ?? "file"} — ${Math.round(progress * 100)}%`
                  : "Uploaded. Extracting text and detecting skills…"}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <Card className="border-primary/40">
          <CardHeader>
            <CardTitle>Confirm your skills</CardTitle>
            <CardDescription>
              We found {result.detected_skills.length} skill
              {result.detected_skills.length === 1 ? "" : "s"} in {result.filename} (
              {result.text_length.toLocaleString()} characters
              {result.page_count ? `, ${result.page_count} page${result.page_count === 1 ? "" : "s"}` : ""}
              ). Accept the ones that are accurate.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {result.already_confirmed.length > 0 ? (
              <Alert>
                <AlertDescription>
                  You already have {result.already_confirmed.join(", ")} in your profile.
                </AlertDescription>
              </Alert>
            ) : null}

            {result.detected_skills.length === 0 ? (
              <EmptyState
                title="No taxonomy skills detected"
                description="Nothing in this document matched the taxonomy. You can add skills manually, or try a CV with a skills section."
                action={{ label: "Add skills manually", onClick: () => router.push("/skills") }}
              />
            ) : (
              <>
                <ul className="divide-y rounded-md border">
                  {result.detected_skills.map((skill) => (
                    <DetectedRow
                      key={skill.skill_id}
                      skill={skill}
                      selection={selections[skill.skill_id] ?? { accepted: false, proficiency: 3 }}
                      disabled={confirmSkills.isPending}
                      onToggle={(accepted) =>
                        setSelections((prev) => ({
                          ...prev,
                          [skill.skill_id]: { ...(prev[skill.skill_id] ?? { proficiency: 3 }), accepted },
                        }))
                      }
                      onProficiency={(proficiency) =>
                        setSelections((prev) => ({
                          ...prev,
                          [skill.skill_id]: { ...(prev[skill.skill_id] ?? { accepted: true }), proficiency },
                        }))
                      }
                    />
                  ))}
                </ul>

                <div className="flex flex-wrap items-center gap-3">
                  <Button onClick={() => void handleConfirm()} disabled={confirmSkills.isPending || acceptedCount === 0}>
                    {confirmSkills.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                    Add {acceptedCount} confirmed skill{acceptedCount === 1 ? "" : "s"}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() =>
                      setSelections((prev) =>
                        Object.fromEntries(
                          Object.entries(prev).map(([id, s]) => [id, { ...s, accepted: true }]),
                        ),
                      )
                    }
                  >
                    Accept all
                  </Button>
                  {confirmed ? (
                    <span className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400" role="status">
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      {confirmed}{" "}
                      <Link href="/skills" className="underline">View your skills</Link>
                    </span>
                  ) : null}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      <section aria-labelledby="uploads-heading" className="space-y-3">
        <h2 id="uploads-heading" className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Your uploads
        </h2>
        {uploads.isPending ? (
          <LoadingRows count={2} />
        ) : uploads.isError ? (
          <ErrorState error={uploads.error} onRetry={() => void uploads.refetch()} />
        ) : (uploads.data?.items ?? []).length === 0 ? (
          <EmptyState
            icon={<FileText className="h-8 w-8" aria-hidden="true" />}
            title="No uploads yet"
            description="Anything you upload appears here, with its detected skills and a delete button."
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {uploads.data?.items.map((upload) => (
              <Card key={upload.id}>
                <CardContent className="space-y-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{upload.original_filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {(upload.size_bytes / 1024).toFixed(0)} KB ·{" "}
                        {upload.created_at ? new Date(upload.created_at).toLocaleDateString() : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge
                        variant={upload.status === "confirmed" ? "secondary" : upload.status === "failed" ? "destructive" : "outline"}
                      >
                        {upload.status}
                      </Badge>
                      <Button
                        variant="ghost" size="icon"
                        onClick={() => setPendingRemoval(upload.id)}
                        aria-label={`Delete ${upload.original_filename}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                  {upload.detected_skills.length > 0 ? (
                    <p className="text-xs text-muted-foreground">
                      {upload.detected_skills.length} skill
                      {upload.detected_skills.length === 1 ? "" : "s"} detected
                    </p>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <ConfirmDialog
        open={pendingRemoval != null}
        onOpenChange={(open) => !open && setPendingRemoval(null)}
        title="Delete this upload?"
        confirmLabel="Delete permanently"
        isPending={deleteUpload.isPending}
        description={
          <>
            <p>The stored file and its extracted text are removed permanently.</p>
            <p className="font-medium text-foreground">
              Kept: any skills you already confirmed from this CV. Those live in your profile
              and are not affected.
            </p>
          </>
        }
        onConfirm={async () => {
          if (pendingRemoval == null) return;
          try { await deleteUpload.mutateAsync(pendingRemoval); }
          catch (error) { setUploadError({ message: errorMessage(error), code: "delete_failed" }); }
          finally { setPendingRemoval(null); }
        }}
      />
    </div>
  );
}

function DetectedRow({
  skill, selection, disabled, onToggle, onProficiency,
}: {
  skill: DetectedSkill;
  selection: Selection;
  disabled: boolean;
  onToggle: (accepted: boolean) => void;
  onProficiency: (proficiency: number) => void;
}) {
  return (
    <li className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <Checkbox
          id={`accept-${skill.skill_id}`}
          checked={selection.accepted}
          disabled={disabled}
          onCheckedChange={(checked) => onToggle(checked === true)}
          className="mt-0.5"
        />
        <label htmlFor={`accept-${skill.skill_id}`} className="min-w-0 flex-1 cursor-pointer">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{skill.canonical_name}</span>
            <Badge variant="outline" className="font-mono text-xs">“{skill.surface_form}”</Badge>
            {skill.already_confirmed ? <Badge variant="secondary">Already added</Badge> : null}
          </span>
          <span className="mt-0.5 block text-xs text-muted-foreground">
            {skill.category} · seen {skill.occurrence_count} time
            {skill.occurrence_count === 1 ? "" : "s"}
          </span>
        </label>
      </div>

      {selection.accepted ? (
        <div className="flex shrink-0 items-center gap-3 sm:w-56">
          <label htmlFor={`prof-${skill.skill_id}`} className="text-xs text-muted-foreground">
            Proficiency
          </label>
          <Slider
            id={`prof-${skill.skill_id}`}
            min={1} max={5} step={1}
            value={[selection.proficiency]}
            disabled={disabled}
            onValueCommit={([value]) => onProficiency(value)}
            className="flex-1"
            aria-label={`Proficiency for ${skill.canonical_name}`}
          />
          <span className="w-6 text-right text-sm font-semibold">{selection.proficiency}</span>
        </div>
      ) : null}
    </li>
  );
}
