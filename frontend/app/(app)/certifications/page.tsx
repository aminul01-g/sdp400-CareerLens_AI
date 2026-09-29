"use client";

/** Certifications. Full C/R/U/D. Separate from education because the shape differs. */
import * as React from "react";
import { Award, Loader2, Pencil, Plus, Trash2, X } from "lucide-react";
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
import type { Certification } from "@/lib/api/types";
import { certificationSchema } from "@/lib/schemas";
import { useCreateCertification, useDeleteCertification, useCertifications, useUpdateCertification } from "@/lib/hooks/use-certifications";

interface FormState { name: string; issuer: string; issuedOn: string; expiresOn: string; credentialUrl: string; }
const EMPTY: FormState = { name: "", issuer: "", issuedOn: "", expiresOn: "", credentialUrl: "" };

export default function CertificationsPage() {
  const certifications = useCertifications();
  const createCertification = useCreateCertification();
  const updateCertification = useUpdateCertification();
  const deleteCertification = useDeleteCertification();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Certification | null>(null);
  const [form, setForm] = React.useState<FormState>(EMPTY);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [notice, setNotice] = React.useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = React.useState<number | null>(null);

  function openCreate() { setEditing(null); setForm(EMPTY); setFieldErrors({}); setDialogOpen(true); }
  function openEdit(cert: Certification) {
    setEditing(cert);
    setForm({
      name: cert.name, issuer: cert.issuer,
      issuedOn: cert.issued_on ?? "", expiresOn: cert.expires_on ?? "",
      credentialUrl: cert.credential_url ?? "",
    });
    setFieldErrors({}); setDialogOpen(true);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFieldErrors({});
    const candidate = {
      name: form.name, issuer: form.issuer,
      issued_on: form.issuedOn || null, expires_on: form.expiresOn || null,
      credential_url: form.credentialUrl || null,
    };
    const parsed = certificationSchema.safeParse(candidate);
    if (!parsed.success) {
      setFieldErrors(Object.fromEntries(parsed.error.issues.map((i) => [String(i.path[0]), i.message])));
      return;
    }
    try {
      if (editing) await updateCertification.mutateAsync({ id: editing.id, ...candidate });
      else await createCertification.mutateAsync(candidate);
      setDialogOpen(false);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) setFieldErrors(error.fieldErrors);
      else setNotice(errorMessage(error, "We could not save that certification."));
    }
  }

  if (certifications.isPending) {
    return <div className="space-y-6"><PageHeader title="Certifications" description="Loading…" /><LoadingRows count={3} /></div>;
  }
  if (certifications.isError) {
    return <div className="space-y-4"><PageHeader title="Certifications" /><ErrorState error={certifications.error} onRetry={() => void certifications.refetch()} /></div>;
  }

  const items = certifications.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Certifications"
        description="Professional certifications, kept separate from degrees because they have an issuer and a credential URL rather than an institution and a grade."
        actions={<Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" aria-hidden="true" />Add a certification</Button>}
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
          icon={<Award className="h-8 w-8" aria-hidden="true" />}
          title="No certifications yet"
          description="Add a certification with its issuer and, optionally, a credential link."
          action={{ label: "Add a certification", onClick: openCreate }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((cert) => (
            <Card key={cert.id}>
              <CardContent className="space-y-2 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{cert.name}</p>
                    <p className="text-sm text-muted-foreground">{cert.issuer}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(cert)} aria-label={`Edit ${cert.name}`}><Pencil className="h-4 w-4" aria-hidden="true" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => setPendingRemoval(cert.id)} aria-label={`Delete ${cert.name}`}><Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" /></Button>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {[
                    cert.issued_on ? `Issued ${cert.issued_on}` : null,
                    cert.expires_on ? `Expires ${cert.expires_on}` : null,
                  ].filter(Boolean).join(" · ") || "No dates recorded"}
                </p>
                {cert.credential_url ? (
                  <a href={cert.credential_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline">
                    View credential
                  </a>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit certification" : "Add a certification"}</DialogTitle>
            <DialogDescription>Name, issuing organisation, and dates.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Deep Learning Specialization" aria-invalid={Boolean(fieldErrors.name)} />
              {fieldErrors.name ? <p className="text-sm text-destructive">{fieldErrors.name}</p> : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="issuer">Issuer</Label>
              <Input id="issuer" value={form.issuer} onChange={(e) => setForm((f) => ({ ...f, issuer: e.target.value }))} placeholder="Example Online University" aria-invalid={Boolean(fieldErrors.issuer)} />
              {fieldErrors.issuer ? <p className="text-sm text-destructive">{fieldErrors.issuer}</p> : null}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="issuedOn">Issued on</Label>
                <Input id="issuedOn" type="date" value={form.issuedOn} onChange={(e) => setForm((f) => ({ ...f, issuedOn: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="expiresOn">Expires on</Label>
                <Input id="expiresOn" type="date" value={form.expiresOn} onChange={(e) => setForm((f) => ({ ...f, expiresOn: e.target.value }))} aria-invalid={Boolean(fieldErrors.expires_on)} />
                {fieldErrors.expires_on ? <p className="text-sm text-destructive">{fieldErrors.expires_on}</p> : null}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="credentialUrl">Credential URL</Label>
              <Input id="credentialUrl" value={form.credentialUrl} onChange={(e) => setForm((f) => ({ ...f, credentialUrl: e.target.value }))} placeholder="https://example.com/credential/123" aria-invalid={Boolean(fieldErrors.credential_url)} />
              {fieldErrors.credential_url ? <p className="text-sm text-destructive">{fieldErrors.credential_url}</p> : null}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createCertification.isPending || updateCertification.isPending}>
                {createCertification.isPending || updateCertification.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {editing ? "Save changes" : "Add certification"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingRemoval != null} onOpenChange={(open) => !open && setPendingRemoval(null)}
        title="Delete this certification?" confirmLabel="Delete" isPending={deleteCertification.isPending}
        description={<p>This permanently removes the certification from your profile.</p>}
        onConfirm={async () => {
          if (pendingRemoval == null) return;
          try { await deleteCertification.mutateAsync(pendingRemoval); }
          catch (error) { setNotice(errorMessage(error)); }
          finally { setPendingRemoval(null); }
        }}
      />
    </div>
  );
}
