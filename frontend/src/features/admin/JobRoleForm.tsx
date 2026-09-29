"use client";

/**
 * Job role editor with the skill-weight control.
 *
 * The weight editor is the reason the schema needs `job_role_skill` as a table
 * with a weight column: the same skill legitimately has different importance in
 * different roles, and a flat list has nowhere to put that. A `Slider` with a live
 * numeric readout, a running total, and a **tier badge that updates as the value
 * moves** is the control that makes the semantic visible — and the badge uses the
 * same 0.8 / 0.5 thresholds the user's gap report will use, so an administrator
 * sees exactly the banding a candidate will see.
 *
 * A bare number input would invite out-of-range values and give no sense of
 * relative importance. That is the difference between a product feature and a
 * database browser.
 */
import * as React from "react";
import { Loader2, Plus, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command, CommandEmpty, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import type { Skill } from "@/lib/api/types";
import { useAdminTaxonomy, useCreateJob } from "@/lib/hooks/use-admin";

const CRITICAL = 0.8;
const IMPORTANT = 0.5;

export type WeightTier = "critical" | "important" | "desirable";

/** The same banding the user-facing gap report uses. */
export function tierOf(weight: number): WeightTier {
  if (weight >= CRITICAL) return "critical";
  if (weight >= IMPORTANT) return "important";
  return "desirable";
}

const TIER_STYLE: Record<WeightTier, string> = {
  critical: "bg-destructive/15 text-destructive border-destructive/30",
  important: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  desirable: "bg-muted text-muted-foreground",
};

interface SelectedSkill {
  skill_id: number;
  name: string;
  category: string;
  weight: number;
}

export function JobRoleForm({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (id: number) => void;
}) {
  const createJob = useCreateJob();
  const taxonomy = useAdminTaxonomy({ q: "" });

  const [title, setTitle] = React.useState("");
  const [family, setFamily] = React.useState("");
  const [seniority, setSeniority] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [selected, setSelected] = React.useState<SelectedSkill[]>([]);
  const [query, setQuery] = React.useState("");
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [formError, setFormError] = React.useState<string | null>(null);

  const total = React.useMemo(
    () => selected.reduce((sum, skill) => sum + skill.weight, 0),
    [selected],
  );

  function reset() {
    setTitle(""); setFamily(""); setSeniority(""); setDescription("");
    setSelected([]); setQuery(""); setFieldErrors({}); setFormError(null);
  }

  function addSkill(skill: Skill) {
    if (selected.some((s) => s.skill_id === skill.id)) return;
    // Start new requirements at "important": genuinely rare for a listed skill to
    // be worthless, and the admin can move it.
    setSelected((prev) => [...prev, { skill_id: skill.id, name: skill.name, category: skill.category, weight: 0.6 }]);
    setPickerOpen(false);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({}); setFormError(null);

    if (selected.length === 0) {
      setFieldErrors({ skills: "A role needs at least one required skill." });
      return;
    }

    try {
      const created = await createJob.mutateAsync({
        title, family, seniority: seniority || null, description,
        responsibilities: [],
        is_active: true,
        skills: selected.map((s) => ({ skill_id: s.skill_id, weight: Number(s.weight.toFixed(2)) })),
      });
      reset();
      onOpenChange(false);
      onCreated?.(created.id);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) setFieldErrors(error.fieldErrors);
      else if (error instanceof ApiError && error.isConflict) setFormError(error.message);
      else setFormError(errorMessage(error, "We could not create that role."));
    }
  }

  const held = new Set(selected.map((s) => s.skill_id));
  const results = (taxonomy.data?.items ?? []).filter((skill) => {
    if (held.has(skill.id)) return false;
    if (!query.trim()) return false;
    const needle = query.toLowerCase();
    return (
      skill.name.toLowerCase().includes(needle) ||
      skill.slug.toLowerCase().includes(needle) ||
      skill.aliases.some((alias) => alias.toLowerCase().includes(needle))
    );
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create a job role</DialogTitle>
          <DialogDescription>
            The description is the text the TF-IDF component matches against, so it must be
            specific. Required skills each carry an importance weight.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {formError ? (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="role-title">Title</Label>
              <Input id="role-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="MLOps Engineer" aria-invalid={Boolean(fieldErrors.title)} />
              {fieldErrors.title ? <p className="text-sm text-destructive">{fieldErrors.title}</p> : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-family">Family</Label>
              <Input id="role-family" value={family} onChange={(e) => setFamily(e.target.value)} placeholder="MLOps" aria-invalid={Boolean(fieldErrors.family)} />
              {fieldErrors.family ? <p className="text-sm text-destructive">{fieldErrors.family}</p> : null}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-seniority">Seniority</Label>
            <Input id="role-seniority" value={seniority} onChange={(e) => setSeniority(e.target.value)} placeholder="Mid" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-description">Description</Label>
            <Textarea
              id="role-description" rows={5} value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this role actually does, in the words a candidate's CV would use."
              aria-invalid={Boolean(fieldErrors.description)}
            />
            {fieldErrors.description ? <p className="text-sm text-destructive">{fieldErrors.description}</p> : null}
          </div>

          <div className="space-y-2">
            <Label>Required skills and their importance</Label>

            {selected.length === 0 ? (
              <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                No skills selected yet. Add at least one.
              </p>
            ) : (
              <ul className="divide-y rounded-md border">
                {selected.map((skill) => {
                  const tier = tierOf(skill.weight);
                  return (
                    <li key={skill.skill_id} className="space-y-2 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{skill.name}</p>
                          <p className="text-xs text-muted-foreground">{skill.category}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <Badge variant="outline" className={TIER_STYLE[tier]}>
                            {tier}
                          </Badge>
                          <span className="w-10 text-right font-mono text-sm tabular-nums">
                            {skill.weight.toFixed(2)}
                          </span>
                          <Button
                            type="button" variant="ghost" size="icon"
                            onClick={() => setSelected((prev) => prev.filter((s) => s.skill_id !== skill.skill_id))}
                            aria-label={`Remove ${skill.name}`}
                          >
                            <X className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Slider
                          min={5} max={100} step={5}
                          value={[Math.round(skill.weight * 100)]}
                          onValueChange={([value]) =>
                            setSelected((prev) =>
                              prev.map((s) => (s.skill_id === skill.skill_id ? { ...s, weight: value / 100 } : s)),
                            )
                          }
                          aria-label={`Importance of ${skill.name}`}
                        />
                        <input
                          type="number" min={0.01} max={1} step={0.05}
                          value={skill.weight}
                          onChange={(event) => {
                            const raw = Number(event.target.value);
                            if (Number.isNaN(raw)) return;
                            // Clamp rather than reject while typing: an empty or
                            // mid-edit field should not throw away the whole list.
                            setSelected((prev) =>
                              prev.map((s) => (s.skill_id === skill.skill_id ? { ...s, weight: Math.min(1, Math.max(0.01, raw)) } : s)),
                            );
                          }}
                          className="h-9 w-20 rounded-md border border-input bg-background px-2 text-sm tabular-nums"
                          aria-label={`Exact importance weight for ${skill.name}`}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
                <PopoverTrigger asChild>
                  <Button type="button" variant="outline" size="sm">
                    <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                    Add a required skill
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command shouldFilter={false}>
                    <CommandInput
                      placeholder="Search the taxonomy (aliases work too)"
                      value={query}
                      onValueChange={setQuery}
                    />
                    <CommandList>
                      <CommandEmpty>
                        {query ? `Nothing matches "${query}".` : "Type to search the taxonomy."}
                      </CommandEmpty>
                      {results.slice(0, 30).map((skill) => (
                        <CommandItem key={skill.id} value={String(skill.id)} onSelect={() => addSkill(skill)}>
                          <div className="flex flex-col">
                            <span>{skill.name}</span>
                            <span className="text-xs text-muted-foreground">{skill.category}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              {selected.length > 0 ? (
                <p className="text-sm text-muted-foreground">
                  {selected.length} skill{selected.length === 1 ? "" : "s"} · total weight{" "}
                  <span className="font-mono tabular-nums">{total.toFixed(2)}</span>
                  <span className="ml-2 text-xs">
                    (only the relative weights matter; the coverage score is scale-invariant)
                  </span>
                </p>
              ) : null}
            </div>

            {fieldErrors.skills ? <p className="text-sm text-destructive">{fieldErrors.skills}</p> : null}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={createJob.isPending}>
              {createJob.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              Create role
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
