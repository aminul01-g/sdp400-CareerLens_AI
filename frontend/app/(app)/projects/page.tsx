"use client";

/**
 * Projects.
 *
 * Full C/R/U/D. The tech-stack input offers taxonomy suggestions because the
 * service canonicalises every entry anyway — a user who types `sklearn` sees it
 * come back as the `scikit-learn` slug, which is the alias index working.
 *
 * An unrecognised technology is shown with a badge rather than rejected: a user may
 * legitimately list a tool the taxonomy has not caught up with.
 */
import * as React from "react";
import { Calendar, ExternalLink, FolderGit2, Loader2, Pencil, Plus, Trash2, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import type { Project } from "@/lib/api/types";
import { projectSchema } from "@/lib/schemas";
import {
  useCreateProject, useDeleteProject, useProjects, useUpdateProject,
} from "@/lib/hooks/use-projects";

interface FormState {
  title: string; description: string; techStack: string; role: string;
  startDate: string; endDate: string; repoUrl: string; isPublic: boolean;
}

const EMPTY: FormState = {
  title: "", description: "", techStack: "", role: "",
  startDate: "", endDate: "", repoUrl: "", isPublic: true,
};

export default function ProjectsPage() {
  const projects = useProjects();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Project | null>(null);
  const [form, setForm] = React.useState<FormState>(EMPTY);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [notice, setNotice] = React.useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = React.useState<number | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY);
    setFieldErrors({});
    setDialogOpen(true);
  }

  function openEdit(project: Project) {
    setEditing(project);
    setForm({
      title: project.title,
      description: project.description,
      techStack: (project.tech_stack ?? []).join(", "),
      role: project.role ?? "",
      startDate: project.start_date ?? "",
      endDate: project.end_date ?? "",
      repoUrl: project.repo_url ?? "",
      isPublic: project.is_public,
    });
    setFieldErrors({});
    setDialogOpen(true);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});

    const candidate = {
      title: form.title,
      description: form.description,
      tech_stack: form.techStack.split(",").map((t) => t.trim()).filter(Boolean),
      role: form.role || null,
      start_date: form.startDate || null,
      end_date: form.endDate || null,
      repo_url: form.repoUrl || null,
      is_public: form.isPublic,
    };
    const parsed = projectSchema.safeParse(candidate);
    if (!parsed.success) {
      setFieldErrors(Object.fromEntries(parsed.error.issues.map((i) => [String(i.path[0]), i.message])));
      return;
    }

    try {
      if (editing) {
        await updateProject.mutateAsync({ id: editing.id, ...candidate });
      } else {
        await createProject.mutateAsync(candidate);
      }
      setDialogOpen(false);
      setNotice(null);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) setFieldErrors(error.fieldErrors);
      else setNotice(errorMessage(error, "We could not save that project."));
    }
  }

  if (projects.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title="Projects" description="Loading your projects…" />
        <LoadingRows count={4} />
      </div>
    );
  }

  if (projects.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Projects" />
        <ErrorState error={projects.error} onRetry={() => void projects.refetch()} />
      </div>
    );
  }

  const items = projects.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        description="What you have built is a first-class signal: project titles, descriptions, and tech stacks all feed the text the engine matches."
        actions={
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Add project
          </Button>
        }
      />

      {notice ? (
        <Alert variant="destructive" role="alert">
          <AlertDescription className="flex items-center justify-between gap-3">
            {notice}
            <Button variant="ghost" size="sm" onClick={() => setNotice(null)}>
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {items.length === 0 ? (
        <EmptyState
          icon={<FolderGit2 className="h-8 w-8" aria-hidden="true" />}
          title="No projects yet"
          description="A project with a real description adds more signal to your profile text than a list of technologies on its own."
          action={{ label: "Add your first project", onClick: openCreate }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((project) => (
            <Card key={project.id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="font-semibold leading-tight">{project.title}</h2>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(project)} aria-label={`Edit ${project.title}`}>
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setPendingRemoval(project.id)} aria-label={`Delete ${project.title}`}>
                      <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                    </Button>
                  </div>
                </div>

                <p className="line-clamp-3 text-sm text-muted-foreground">{project.description}</p>

                {(project.tech_stack ?? []).length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {project.tech_stack.map((tech) => (
                      <Badge key={tech} variant="secondary">{tech}</Badge>
                    ))}
                    {project.unrecognised_tech.map((tech) => (
                      <Badge key={tech} variant="outline" className="border-dashed">
                        {tech} · not in taxonomy
                      </Badge>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  {project.role ? <span>{project.role}</span> : null}
                  {project.start_date ? (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" aria-hidden="true" />
                      {project.start_date}
                      {project.end_date ? ` – ${project.end_date}` : " – present"}
                    </span>
                  ) : null}
                  {project.repo_url ? (
                    <a
                      href={project.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-primary hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      Repository
                    </a>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit project" : "Add a project"}</DialogTitle>
            <DialogDescription>
              Describe what you built and what you built it with. Both contribute to your
              profile text.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="Real-time sales dashboard" aria-invalid={Boolean(fieldErrors.title)} />
              {fieldErrors.title ? <p className="text-sm text-destructive">{fieldErrors.title}</p> : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" rows={4} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="What it does, what you built it with, and what the outcome was." aria-invalid={Boolean(fieldErrors.description)} />
              {fieldErrors.description ? <p className="text-sm text-destructive">{fieldErrors.description}</p> : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="techStack">Technologies</Label>
              <Input
                id="techStack" value={form.techStack}
                onChange={(e) => setForm((f) => ({ ...f, techStack: e.target.value }))}
                placeholder="python, sklearn, fastapi, docker"
                aria-describedby="tech-hint"
              />
              <p id="tech-hint" className="text-xs text-muted-foreground">
                Comma separated. Each is matched against the taxonomy and stored as its
                canonical slug, so &quot;sklearn&quot; and &quot;Scikit-learn&quot; stay the same fact.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="role">Your role</Label>
                <Input id="role" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))} placeholder="Solo developer" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="repoUrl">Repository URL</Label>
                <Input id="repoUrl" value={form.repoUrl} onChange={(e) => setForm((f) => ({ ...f, repoUrl: e.target.value }))} placeholder="https://github.com/you/project" aria-invalid={Boolean(fieldErrors.repo_url)} />
                {fieldErrors.repo_url ? <p className="text-sm text-destructive">{fieldErrors.repo_url}</p> : null}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="startDate">Start date</Label>
                <Input id="startDate" type="date" value={form.startDate} onChange={(e) => setForm((f) => ({ ...f, startDate: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate">End date</Label>
                <Input id="endDate" type="date" value={form.endDate} onChange={(e) => setForm((f) => ({ ...f, endDate: e.target.value }))} aria-invalid={Boolean(fieldErrors.end_date)} />
                {fieldErrors.end_date ? <p className="text-sm text-destructive">{fieldErrors.end_date}</p> : null}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="isPublic" type="checkbox" checked={form.isPublic}
                onChange={(e) => setForm((f) => ({ ...f, isPublic: e.target.checked }))}
                className="h-4 w-4 rounded border-input"
              />
              <Label htmlFor="isPublic" className="font-normal">Visible on my profile</Label>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createProject.isPending || updateProject.isPending}>
                {createProject.isPending || updateProject.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                {editing ? "Save changes" : "Add project"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingRemoval != null}
        onOpenChange={(open) => !open && setPendingRemoval(null)}
        title="Delete this project?"
        confirmLabel="Delete"
        isPending={deleteProject.isPending}
        description={<p>This permanently removes the project from your profile. It cannot be undone.</p>}
        onConfirm={async () => {
          if (pendingRemoval == null) return;
          try {
            await deleteProject.mutateAsync(pendingRemoval);
          } catch (error) {
            setNotice(errorMessage(error));
          } finally {
            setPendingRemoval(null);
          }
        }}
      />
    </div>
  );
}
