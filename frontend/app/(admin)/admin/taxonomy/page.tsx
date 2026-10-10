"use client";

/**
 * Skill taxonomy editor.
 *
 * The taxonomy is the vocabulary the whole recommendation engine is written in:
 * 151 skills that 756 declared aliases resolve to, which job-role requirements
 * are expressed in, and which user profiles are matched against. Editing it is
 * therefore a knowledge-base change, not a content edit — which is why this page
 * shows the alias count and the resolved slug next to every row.
 *
 * Aliases are the part that matters most and the easiest to get wrong. A surface
 * form nobody declares is a surface form the extractor cannot resolve, so the
 * form makes adding them a first-class field rather than a detail.
 *
 * Deleting a skill is refused by the API when a job role or a user still
 * references it. That is the correct behaviour — a silent cascade would quietly
 * change every recommendation — so the error is surfaced verbatim instead of
 * being flattened into a generic failure.
 */
import * as React from "react";
import { Loader2, Pencil, Plus, Save, Tags, Trash2, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { errorMessage } from "@/lib/api/client";
import {
  useAdminTaxonomy,
  useCreateTaxonomySkill,
  useDeleteTaxonomySkill,
  useUpdateTaxonomySkill,
} from "@/lib/hooks/use-admin";
import type { Skill } from "@/lib/api/types";

const ALL = "__all__";
const PAGE_SIZE = 50;

interface SkillDraft {
  name: string;
  category: string;
  description: string;
  /** Raw textarea content; split on commas when saved. */
  aliases: string;
}

const emptyDraft: SkillDraft = { name: "", category: "", description: "", aliases: "" };

const draftFrom = (skill: Skill): SkillDraft => ({
  name: skill.name,
  category: skill.category,
  description: skill.description ?? "",
  aliases: skill.aliases.join(", "),
});

/**
 * Aliases arrive as free text. Split on commas, trim, drop blanks, and
 * de-duplicate case-insensitively while keeping the first spelling seen — the
 * same normalisation the seed scripts apply.
 */
function parseAliases(raw: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(",")) {
    const value = part.trim();
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
}

export default function AdminTaxonomyPage() {
  const [query, setQuery] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [category, setCategory] = React.useState(ALL);
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  // A changed filter invalidates the current page number: staying on page 4 of a
  // narrower result set shows an empty table for no reason.
  React.useEffect(() => {
    setPage(1);
  }, [debounced, category]);

  const taxonomy = useAdminTaxonomy({
    q: debounced || undefined,
    category: category === ALL ? undefined : category,
    page,
  });
  const createSkill = useCreateTaxonomySkill();
  const updateSkill = useUpdateTaxonomySkill();
  const deleteSkill = useDeleteTaxonomySkill();

  const [editorOpen, setEditorOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Skill | null>(null);
  const [draft, setDraft] = React.useState<SkillDraft>(emptyDraft);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = React.useState<Skill | null>(null);

  const items = taxonomy.data?.items ?? [];
  const total = taxonomy.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // The category filter can only offer categories that exist, and the API has no
  // endpoint for the distinct list, so it is derived from what is already loaded
  // and is therefore a convenience rather than an exhaustive filter.
  const categories = React.useMemo(
    () => [...new Set(items.map((skill) => skill.category))].sort(),
    [items],
  );

  function openCreate() {
    setEditing(null);
    setDraft(emptyDraft);
    setFormError(null);
    setEditorOpen(true);
  }

  function openEdit(skill: Skill) {
    setEditing(skill);
    setDraft(draftFrom(skill));
    setFormError(null);
    setEditorOpen(true);
  }

  async function submit() {
    setFormError(null);
    const name = draft.name.trim();
    const skillCategory = draft.category.trim();
    if (!name) return setFormError("A skill needs a name.");
    if (!skillCategory) return setFormError("A skill needs a category.");
    if (editing && !draft.description.trim()) {
      return setFormError("A skill needs a description.");
    }

    const body = {
      name,
      category: skillCategory,
      description: draft.description.trim() || undefined,
      aliases: parseAliases(draft.aliases),
    };

    try {
      if (editing) {
        await updateSkill.mutateAsync({ id: editing.id, ...body });
        setNotice(`Updated ${name}.`);
      } else {
        await createSkill.mutateAsync(body);
        setNotice(`Created ${name}.`);
        // The table is paginated and ordered by name, so a new skill can land on
        // the last page — creating something and not seeing it is the worst
        // possible outcome. Filter to it so the row that was just written is the
        // one on screen.
        setQuery(name);
        setCategory(ALL);
      }
      setEditorOpen(false);
    } catch (error) {
      setFormError(errorMessage(error, "We could not save that skill."));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Taxonomy"
        description="The vocabulary the engine matches in. Aliases are the surface forms a CV or a profile is allowed to use and still resolve to the same skill."
        actions={
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            New skill
          </Button>
        }
      />

      {notice ? (
        <Alert role="status">
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="taxonomy-search">Search</Label>
          <Input
            id="taxonomy-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name, slug or alias"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="taxonomy-category">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger id="taxonomy-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All categories</SelectItem>
              {categories.map((value) => (
                <SelectItem key={value} value={value}>
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {taxonomy.isPending ? (
        <Card>
          <CardContent className="p-4">
            <LoadingRows count={6} />
          </CardContent>
        </Card>
      ) : taxonomy.isError ? (
        <ErrorState error={taxonomy.error} onRetry={() => void taxonomy.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Tags className="h-8 w-8" aria-hidden="true" />}
          title="No skills match"
          description="Adjust the search or category, or add the first skill."
          action={{ label: "New skill", onClick: openCreate }}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <caption className="sr-only">Skills in the taxonomy</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">Aliases</TableHead>
                    <TableHead className="w-24 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((skill) => (
                    <TableRow key={skill.id}>
                      <TableCell>
                        <p className="font-medium">{skill.name}</p>
                        {skill.description ? (
                          <p className="max-w-md truncate text-xs text-muted-foreground">
                            {skill.description}
                          </p>
                        ) : null}
                        {skill.aliases.length > 0 ? (
                          // A div, not a p: Badge renders a div, and a div inside a
                          // p is invalid HTML that React reports as a hydration error.
                          <div className="mt-1 flex flex-wrap gap-1">
                            {skill.aliases.slice(0, 6).map((alias) => (
                              <Badge key={alias} variant="secondary" className="font-mono text-[10px]">
                                {alias}
                              </Badge>
                            ))}
                            {skill.aliases.length > 6 ? (
                              <Badge variant="secondary" className="text-[10px]">
                                +{skill.aliases.length - 6}
                              </Badge>
                            ) : null}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{skill.slug}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{skill.category}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{skill.aliases.length}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label={`Edit ${skill.name}`}
                            onClick={() => openEdit(skill)}
                          >
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label={`Delete ${skill.name}`}
                            onClick={() => setPendingDelete(skill)}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {total} skill(s) match.
          {category !== ALL || debounced ? " Clear the filters to see the whole taxonomy." : null}
        </p>
        {pageCount > 1 ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {page} of {pageCount}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || taxonomy.isFetching}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={page >= pageCount || taxonomy.isFetching}
            >
              Next
            </Button>
          </div>
        ) : null}
      </div>

      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editing ? `Edit ${editing.name}` : "Create a skill"}</DialogTitle>
            <DialogDescription>
              The name is what a user picks from the picker. Aliases are the other spellings the
              extractor will fold into this skill — a CV saying &ldquo;postgres&rdquo; resolves
              here only if that alias is declared.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {formError ? (
              <Alert variant="destructive" role="alert">
                <AlertTitle>That could not be saved</AlertTitle>
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="skill-name">Name</Label>
              <Input
                id="skill-name"
                value={draft.name}
                onChange={(event) => setDraft((d) => ({ ...d, name: event.target.value }))}
                aria-invalid={!draft.name.trim()}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="skill-category">Category</Label>
              <Input
                id="skill-category"
                list="taxonomy-categories"
                value={draft.category}
                onChange={(event) => setDraft((d) => ({ ...d, category: event.target.value }))}
                placeholder="e.g. MLOps & Cloud"
              />
              <datalist id="taxonomy-categories">
                {categories.map((value) => (
                  <option key={value} value={value} />
                ))}
              </datalist>
            </div>

            <div className="space-y-2">
              <Label htmlFor="skill-description">Description</Label>
              <Textarea
                id="skill-description"
                rows={3}
                value={draft.description}
                onChange={(event) => setDraft((d) => ({ ...d, description: event.target.value }))}
                placeholder="What this skill is and when it counts"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="skill-aliases">Aliases</Label>
              <Textarea
                id="skill-aliases"
                rows={3}
                value={draft.aliases}
                onChange={(event) => setDraft((d) => ({ ...d, aliases: event.target.value }))}
                placeholder="comma separated, e.g. postgres, postgresql, psql"
              />
              <p className="text-xs text-muted-foreground">
                {parseAliases(draft.aliases).length} alias(es) will be saved.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditorOpen(false)}>
              <X className="mr-2 h-4 w-4" aria-hidden="true" />
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={createSkill.isPending || updateSkill.isPending}>
              {createSkill.isPending || updateSkill.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Save className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {editing ? "Save changes" : "Create skill"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={`Delete ${pendingDelete?.name ?? "this skill"}?`}
        confirmLabel="Delete skill"
        isPending={deleteSkill.isPending}
        description={
          <>
            <p>
              This removes the skill and its{" "}
              {pendingDelete?.aliases.length ?? 0} alias(es) from the vocabulary.
            </p>
            <p className="font-medium text-foreground">
              If any job role requires it, or any user has already added it to their profile,
              the deletion is refused. Detach it from those first — a silent cascade here would
              quietly change every recommendation.
            </p>
          </>
        }
        onConfirm={async () => {
          if (!pendingDelete) return;
          const name = pendingDelete.name;
          try {
            await deleteSkill.mutateAsync(pendingDelete.id);
            setPendingDelete(null);
            setNotice(`Deleted ${name}.`);
          } catch (error) {
            setPendingDelete(null);
            setNotice(errorMessage(error, "We could not delete that skill."));
          }
        }}
      />
    </div>
  );
}
