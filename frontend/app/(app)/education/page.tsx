"use client";

/** Education records. Full C/R/U/D, with year-range validation on both sides. */
import * as React from "react";
import { GraduationCap, Loader2, Pencil, Plus, Trash2, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import type { EducationRecord } from "@/lib/api/types";
import { educationSchema } from "@/lib/schemas";
import { useCreateEducation, useDeleteEducation, useEducation, useUpdateEducation } from "@/lib/hooks/use-education";

interface FormState {
  institution: string; degree: string; fieldOfStudy: string;
  startYear: string; endYear: string; grade: string;
}
const EMPTY: FormState = { institution: "", degree: "", fieldOfStudy: "", startYear: "", endYear: "", grade: "" };

export default function EducationPage() {
  const education = useEducation();
  const createEducation = useCreateEducation();
  const updateEducation = useUpdateEducation();
  const deleteEducation = useDeleteEducation();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<EducationRecord | null>(null);
  const [form, setForm] = React.useState<FormState>(EMPTY);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [notice, setNotice] = React.useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = React.useState<number | null>(null);

  function openCreate() { setEditing(null); setForm(EMPTY); setFieldErrors({}); setDialogOpen(true); }
  function openEdit(record: EducationRecord) {
    setEditing(record);
    setForm({
      institution: record.institution, degree: record.degree,
      fieldOfStudy: record.field_of_study ?? "",
      startYear: record.start_year != null ? String(record.start_year) : "",
      endYear: record.end_year != null ? String(record.end_year) : "",
      grade: record.grade ?? "",
    });
    setFieldErrors({}); setDialogOpen(true);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFieldErrors({});
    const num = (v: string) => (v.trim() === "" ? null : Number(v));
    const candidate = {
      institution: form.institution, degree: form.degree,
      field_of_study: form.fieldOfStudy || null,
      start_year: num(form.startYear), end_year: num(form.endYear),
      grade: form.grade || null,
    };
    const parsed = educationSchema.safeParse(candidate);
    if (!parsed.success) {
      setFieldErrors(Object.fromEntries(parsed.error.issues.map((i) => [String(i.path[0]), i.message])));
      return;
    }
    try {
      if (editing) await updateEducation.mutateAsync({ id: editing.id, ...candidate });
      else await createEducation.mutateAsync(candidate);
      setDialogOpen(false);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) setFieldErrors(error.fieldErrors);
      else setNotice(errorMessage(error, "We could not save that record."));
    }
  }

  if (education.isPending) {
    return <div className="space-y-6"><PageHeader title="Education" description="Loading…" /><LoadingRows count={3} /></div>;
  }
  if (education.isError) {
    return <div className="space-y-4"><PageHeader title="Education" /><ErrorState error={education.error} onRetry={() => void education.refetch()} /></div>;
  }

  const items = education.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Education"
        description="Degrees contribute to your profile text, so the matching engine can see your background."
        actions={<Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" aria-hidden="true" />Add a degree</Button>}
      />

      {notice ? (
        <Alert variant="destructive" role="alert">
          <AlertDescription className="flex items-center justify-between gap-3">
            {notice}
            <Button variant="ghost" size="sm" onClick={() => setNotice(null)}><X className="h-3.5 w-3.5" aria-hidden="true" /></Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {items.length === 0 ? (
        <EmptyState
          icon={<GraduationCap className="h-8 w-8" aria-hidden="true" />}
          title="No education records yet"
          description="Add a degree, its field of study, and the institution."
          action={{ label: "Add a degree", onClick: openCreate }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((record) => (
            <Card key={record.id}>
              <CardContent className="space-y-2 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{record.degree}</p>
                    <p className="text-sm text-muted-foreground">{record.institution}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(record)} aria-label={`Edit ${record.degree}`}><Pencil className="h-4 w-4" aria-hidden="true" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => setPendingRemoval(record.id)} aria-label={`Delete ${record.degree}`}><Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" /></Button>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {[record.field_of_study, [record.start_year, record.end_year].filter(Boolean).join(" – "), record.grade]
                    .filter(Boolean).join(" · ")}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit degree" : "Add a degree"}</DialogTitle>
            <DialogDescription>Institution, degree, field of study, and years.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="institution">Institution</Label>
              <Input id="institution" value={form.institution} onChange={(e) => setForm((f) => ({ ...f, institution: e.target.value }))} aria-invalid={Boolean(fieldErrors.institution)} />
              {fieldErrors.institution ? <p className="text-sm text-destructive">{fieldErrors.institution}</p> : null}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="degree">Degree</Label>
                <Input id="degree" value={form.degree} onChange={(e) => setForm((f) => ({ ...f, degree: e.target.value }))} placeholder="BSc" aria-invalid={Boolean(fieldErrors.degree)} />
                {fieldErrors.degree ? <p className="text-sm text-destructive">{fieldErrors.degree}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="fieldOfStudy">Field of study</Label>
                <Input id="fieldOfStudy" value={form.fieldOfStudy} onChange={(e) => setForm((f) => ({ ...f, fieldOfStudy: e.target.value }))} placeholder="Computer Science" />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="startYear">Start year</Label>
                <Input id="startYear" type="number" value={form.startYear} onChange={(e) => setForm((f) => ({ ...f, startYear: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endYear">End year</Label>
                <Input id="endYear" type="number" value={form.endYear} onChange={(e) => setForm((f) => ({ ...f, endYear: e.target.value }))} aria-invalid={Boolean(fieldErrors.end_year)} />
                {fieldErrors.end_year ? <p className="text-sm text-destructive">{fieldErrors.end_year}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="grade">Grade / CGPA</Label>
                <Input id="grade" value={form.grade} onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))} placeholder="First Class" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createEducation.isPending || updateEducation.isPending}>
                {createEducation.isPending || updateEducation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {editing ? "Save changes" : "Add degree"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingRemoval != null} onOpenChange={(open) => !open && setPendingRemoval(null)}
        title="Delete this education record?" confirmLabel="Delete" isPending={deleteEducation.isPending}
        description={<p>This permanently removes the record from your profile.</p>}
        onConfirm={async () => {
          if (pendingRemoval == null) return;
          try { await deleteEducation.mutateAsync(pendingRemoval); }
          catch (error) { setNotice(errorMessage(error)); }
          finally { setPendingRemoval(null); }
        }}
      />
    </div>
  );
}
