"use client";

/**
 * Job role editor.
 *
 * Edit the role's fields and its weighted required-skill set. The skill set is
 * saved with a **full replacement** (`PUT`), not a diff — the same atomic
 * operation the create form uses, so a validation failure leaves the previous set
 * intact rather than leaving a role with half its requirements.
 *
 * Deletion is deliberately awkward: if any stored recommendation run references
 * the role, the API returns `409 conflict_role_in_use` and the UI explains that
 * deactivating is the right action. Destroying users' recommendation history
 * because an admin removed a role is a worse outcome than an orphaned title.
 */
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import * as React from "react";
import { ArrowLeft, Loader2, Plus, Save, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import {
  useAdminJob, useAdminTaxonomy, useDeleteJob, useReplaceJobSkills, useUpdateJob,
} from "@/lib/hooks/use-admin";
import { tierOf, type WeightTier } from "@/features/admin/JobRoleForm";

const TIER_STYLE: Record<WeightTier, string> = {
  critical: "bg-destructive/15 text-destructive border-destructive/30",
  important: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  desirable: "bg-muted text-muted-foreground",
};

export default function AdminJobEditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const roleId = Number(params?.id);

  const role = useAdminJob(Number.isFinite(roleId) ? roleId : null);
  const updateJob = useUpdateJob();
  const replaceSkills = useReplaceJobSkills();
  const deleteJob = useDeleteJob();
  const taxonomy = useAdminTaxonomy({ q: "" });

  const [form, setForm] = React.useState({
    title: "", family: "", seniority: "", description: "", is_active: true,
  });
  const [weights, setWeights] = React.useState<Record<number, { name: string; category: string; weight: number }>>({});
  const [candidate, setCandidate] = React.useState("");
  const [notice, setNotice] = React.useState<string | null>(null);
  const [fieldError, setFieldError] = React.useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);

  React.useEffect(() => {
    if (!role.data) return;
    setForm({
      title: role.data.title,
      family: role.data.family,
      seniority: role.data.seniority ?? "",
      description: role.data.description,
      is_active: role.data.is_active,
    });
    setWeights(
      Object.fromEntries(
        role.data.skills.map((s) => [s.skill_id, { name: s.name, category: s.category, weight: Number(s.weight) }]),
      ),
    );
    setDirty(false);
  }, [role.data]);

  if (role.isPending) return <LoadingPage label="Loading the role" />;
  if (role.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Job role" />
        <ErrorState error={role.error} onRetry={() => void role.refetch()} />
      </div>
    );
  }

  const skillIds = Object.keys(weights).map(Number);
  const total = Object.values(weights).reduce((sum, s) => sum + s.weight, 0);

  const available = (taxonomy.data?.items ?? [])
    .filter((skill) => !(skill.id in weights))
    .filter((skill) => {
      if (!candidate.trim()) return false;
      const needle = candidate.toLowerCase();
      return (
        skill.name.toLowerCase().includes(needle) ||
        skill.aliases.some((alias) => alias.toLowerCase().includes(needle))
      );
    });

  async function saveFields() {
    setNotice(null); setFieldError(null);
    try {
      await updateJob.mutateAsync({
        id: roleId,
        title: form.title,
        family: form.family,
        seniority: form.seniority || null,
        description: form.description,
        is_active: form.is_active,
      });
      setNotice("Saved.");
      setDirty(false);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        setFieldError(error.fieldErrors.title ?? error.fieldErrors.description ?? error.message);
      } else {
        setNotice(errorMessage(error, "We could not save the role."));
      }
    }
  }

  async function saveSkills() {
    setNotice(null); setFieldError(null);
    if (skillIds.length === 0) {
      setFieldError("A role needs at least one required skill.");
      return;
    }
    try {
      await replaceSkills.mutateAsync({
        id: roleId,
        skills: skillIds.map((id) => ({ skill_id: id, weight: Number(weights[id].weight.toFixed(2)) })),
      });
      setNotice("Required skills saved.");
      setCandidate("");
      setDirty(false);
    } catch (error) {
      // The API replaces atomically, so a failure here means the previous set is
      // still intact — say so, because the admin's next question would be exactly that.
      setFieldError(`${errorMessage(error)} Your previous requirement set was not changed.`);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={role.data.title}
        description={`${role.data.family}${role.data.seniority ? ` · ${role.data.seniority}` : ""}`}
        actions={
          <>
            <Button variant="outline" asChild>
              <Link href="/admin/jobs"><ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />All roles</Link>
            </Button>
            <Button variant="destructive" onClick={() => setConfirmOpen(true)}>Delete role</Button>
          </>
        }
      />

      {notice ? <Alert role="status"><AlertDescription>{notice}</AlertDescription></Alert> : null}
      {fieldError ? <Alert variant="destructive" role="alert"><AlertDescription>{fieldError}</AlertDescription></Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle>Role details</CardTitle>
          <CardDescription>
            The description is the corpus document for the TF-IDF component, so specific wording
            matters more than generalities.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="edit-title">Title</Label>
              <Input id="edit-title" value={form.title} onChange={(e) => { setForm((f) => ({ ...f, title: e.target.value })); setDirty(true); }} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-family">Family</Label>
              <Input id="edit-family" value={form.family} onChange={(e) => { setForm((f) => ({ ...f, family: e.target.value })); setDirty(true); }} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-seniority">Seniority</Label>
            <Input id="edit-seniority" value={form.seniority} onChange={(e) => { setForm((f) => ({ ...f, seniority: e.target.value })); setDirty(true); }} placeholder="Mid" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-description">Description</Label>
            <Textarea id="edit-description" rows={6} value={form.description} onChange={(e) => { setForm((f) => ({ ...f, description: e.target.value })); setDirty(true); }} />
          </div>

          <div className="flex items-center gap-3">
            <Switch id="edit-active" checked={form.is_active} onCheckedChange={(checked) => { setForm((f) => ({ ...f, is_active: checked })); setDirty(true); }} />
            <Label htmlFor="edit-active" className="font-normal">
              Active — inactive roles are hidden from new recommendations
            </Label>
          </div>

          <Button onClick={() => void saveFields()} disabled={updateJob.isPending}>
            {updateJob.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="mr-2 h-4 w-4" aria-hidden="true" />}
            Save details
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Required skills and importance weights</CardTitle>
          <CardDescription>
            Saved as one atomic replacement. A validation failure leaves the current set
            untouched.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="divide-y rounded-md border">
            {skillIds.map((id) => {
              const skill = weights[id];
              const tier = tierOf(skill.weight);
              return (
                <li key={id} className="space-y-2 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{skill.name}</p>
                      <p className="text-xs text-muted-foreground">{skill.category}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="outline" className={TIER_STYLE[tier]}>{tier}</Badge>
                      <span className="w-10 text-right font-mono text-sm tabular-nums">{skill.weight.toFixed(2)}</span>
                      <Button variant="ghost" size="icon" onClick={() => { setWeights((w) => { const next = { ...w }; delete next[id]; return next; }); setDirty(true); }} aria-label={`Remove ${skill.name}`}>
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                  <Slider
                    min={5} max={100} step={5}
                    value={[Math.round(skill.weight * 100)]}
                    onValueChange={([value]) => { setWeights((w) => ({ ...w, [id]: { ...w[id], weight: value / 100 } })); setDirty(true); }}
                    aria-label={`Importance of ${skill.name}`}
                  />
                </li>
              );
            })}
          </ul>

          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-64 flex-1 space-y-2">
              <Label htmlFor="add-skill">Add a required skill</Label>
              <Input
                id="add-skill" value={candidate}
                onChange={(e) => setCandidate(e.target.value)}
                placeholder="Search the taxonomy — aliases work too"
              />
              {candidate.trim() ? (
                <ul className="max-h-48 divide-y overflow-y-auto rounded-md border">
                  {available.slice(0, 20).map((skill) => (
                    <li key={skill.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 p-2 text-left text-sm hover:bg-accent"
                        onClick={() => {
                          setWeights((w) => ({ ...w, [skill.id]: { name: skill.name, category: skill.category, weight: 0.6 } }));
                          setCandidate("");
                          setDirty(true);
                        }}
                      >
                        <span className="min-w-0 truncate">{skill.name}</span>
                        <Plus className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                  {available.length === 0 ? (
                    <li className="p-2 text-sm text-muted-foreground">No match in the taxonomy.</li>
                  ) : null}
                </ul>
              ) : null}
            </div>
            <div className="text-sm text-muted-foreground">
              {skillIds.length} skill{skillIds.length === 1 ? "" : "s"} · total weight{" "}
              <span className="font-mono tabular-nums">{total.toFixed(2)}</span>
            </div>
          </div>

          <Button onClick={() => void saveSkills()} disabled={replaceSkills.isPending}>
            {replaceSkills.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="mr-2 h-4 w-4" aria-hidden="true" />}
            Save required skills
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen} onOpenChange={setConfirmOpen}
        title="Delete this job role?" confirmLabel="Delete role" isPending={deleteJob.isPending}
        description={
          <>
            <p>This permanently removes the role and its {skillIds.length} required skill(s).</p>
            <p className="font-medium text-foreground">
              If any stored recommendation run references this role, the deletion is refused
              with a conflict error. Deactivate the role instead — that hides it from new
              recommendations while preserving every user&apos;s stored results.
            </p>
          </>
        }
        onConfirm={async () => {
          try {
            await deleteJob.mutateAsync(roleId);
            setConfirmOpen(false);
            router.push("/admin/jobs");
          } catch (error) {
            setConfirmOpen(false);
            setNotice(errorMessage(error, "We could not delete that role."));
          }
        }}
      />

      {dirty ? (
        <p className="text-sm text-amber-600 dark:text-amber-400" role="status">
          You have unsaved changes.
        </p>
      ) : null}
    </div>
  );
}
