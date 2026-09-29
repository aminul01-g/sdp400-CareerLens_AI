"use client";

/**
 * Skill manager.
 *
 * The primary data-entry screen for the engine: without skills there is nothing to
 * match on, which is why this one has both a taxonomy search *and* a link to CV
 * upload in its empty state.
 *
 * The search box matches **aliases**, so typing `sklearn` finds `Scikit-learn`.
 * That is the taxonomy's alias feature made visible, and it teaches the user the
 * vocabulary the system reasons in.
 */
import * as React from "react";
import { Loader2, Plus, Sparkles, Trash2, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Command, CommandEmpty, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingRows } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import type { Skill } from "@/lib/api/types";
import {
  useAddSkill, useRemoveSkill, useTaxonomySearch, useUpdateSkill, useUserSkills,
} from "@/lib/hooks/use-skills";

const PROFILE_SOURCE = { manual: "Added manually", cv_extracted: "From your CV" } as const;

export default function SkillsPage() {
  const skills = useUserSkills();
  const [query, setQuery] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [category, setCategory] = React.useState<string>("all");
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [pendingRemoval, setPendingRemoval] = React.useState<number | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);

  const addSkill = useAddSkill();
  const updateSkill = useUpdateSkill();
  const removeSkill = useRemoveSkill();

  // Debounced so typing does not fire a request per keystroke.
  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const held = React.useMemo(
    () => new Set((skills.data ?? []).map((s) => s.skill_id)),
    [skills.data],
  );

  const taxonomy = useTaxonomySearch({
    q: debounced,
    category: category === "all" ? undefined : category,
    limit: 50,
  });

  const categories = React.useMemo(() => {
    const found = new Set((skills.data ?? []).map((s) => s.category));
    return Array.from(found).sort();
  }, [skills.data]);

  async function handleAdd(skill: Skill) {
    setNotice(null);
    try {
      await addSkill.mutateAsync({ skill_id: skill.id, proficiency: 3 });
      setPickerOpen(false);
      setQuery("");
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        setNotice(`You have already added ${skill.name}.`);
      } else {
        setNotice(errorMessage(error, "We could not add that skill."));
      }
    }
  }

  if (skills.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title="Skills" description="Loading your skills…" />
        <LoadingRows count={6} />
      </div>
    );
  }

  if (skills.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Skills" />
        <ErrorState error={skills.error} onRetry={() => void skills.refetch()} />
      </div>
    );
  }

  const items = skills.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Skills"
        description="Skills are chosen from a curated taxonomy and carry a proficiency from 1 to 5. These are what the recommendation engine scores you against."
        actions={
          <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
            <PopoverTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                Add skill
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="end">
              <Command shouldFilter={false}>
                <CommandInput
                  placeholder="Search by name or alias (try &quot;sklearn&quot;)"
                  value={query}
                  onValueChange={setQuery}
                />
                {categories.length > 0 ? (
                  <div className="border-b p-2">
                    <Select value={category} onValueChange={setCategory}>
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All categories</SelectItem>
                        {categories.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ) : null}
                <CommandList>
                  {taxonomy.isFetching ? (
                    <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Searching…
                    </div>
                  ) : (
                    <CommandEmpty>
                      {debounced
                        ? `No taxonomy entry matches "${debounced}".`
                        : "Type at least one character to search the taxonomy."}
                    </CommandEmpty>
                  )}
                  {taxonomy.data?.items.map((skill) => {
                    const already = held.has(skill.id);
                    return (
                      <CommandItem
                        key={skill.id}
                        value={String(skill.id)}
                        disabled={already}
                        onSelect={() => void handleAdd(skill)}
                        className="flex-col items-start gap-0.5 py-2"
                      >
                        <div className="flex w-full items-center gap-2">
                          <span className="font-medium">{skill.name}</span>
                          {already ? (
                            <Badge variant="secondary" className="ml-auto">Added</Badge>
                          ) : null}
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {skill.category}
                          {skill.aliases.length > 0
                            ? ` · also: ${skill.aliases.slice(0, 3).join(", ")}`
                            : ""}
                        </span>
                      </CommandItem>
                    );
                  })}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        }
      />

      {notice ? (
        <Alert role="status">
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
          icon={<Sparkles className="h-8 w-8" aria-hidden="true" />}
          title="No skills yet"
          description="Search the curated taxonomy to add skills, or upload your CV and we will suggest some for you to confirm."
          action={{ label: "Search the taxonomy", onClick: () => setPickerOpen(true) }}
          secondaryAction={{ label: "Upload your CV", href: "/resume" }}
        />
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {items.length} skill{items.length === 1 ? "" : "s"} · proficiency is how strongly
            you have worked with each one, and it scales your coverage score
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {items.map((item) => (
              <Card key={item.skill_id}>
                <CardContent className="space-y-3 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.name}</p>
                      <p className="text-xs text-muted-foreground">{item.category}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <Badge variant={item.source === "cv_extracted" ? "secondary" : "outline"}>
                        {PROFILE_SOURCE[item.source] ?? item.source}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setPendingRemoval(item.skill_id)}
                        aria-label={`Remove ${item.name}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <label htmlFor={`prof-${item.skill_id}`}>Proficiency</label>
                      <span className="font-semibold">{item.proficiency} / 5</span>
                    </div>
                    <Slider
                      id={`prof-${item.skill_id}`}
                      min={1}
                      max={5}
                      step={1}
                      value={[item.proficiency]}
                      disabled={updateSkill.isPending}
                      onValueCommit={([value]) => {
                        void updateSkill
                          .mutateAsync({ skillId: item.skill_id, proficiency: value })
                          .catch((error) => setNotice(errorMessage(error)));
                      }}
                      aria-label={`Proficiency for ${item.name}`}
                    />
                    <div className="flex justify-between px-0.5 text-xs text-muted-foreground" aria-hidden="true">
                      <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      <ConfirmDialog
        open={pendingRemoval != null}
        onOpenChange={(open) => !open && setPendingRemoval(null)}
        title="Remove this skill?"
        confirmLabel="Remove"
        isPending={removeSkill.isPending}
        description={
          <p>
            This removes the skill from your profile. It will lower your coverage against any
            role that requires it, and your stored recommendation runs keep their recorded
            scores unchanged.
          </p>
        }
        onConfirm={async () => {
          if (pendingRemoval == null) return;
          try {
            await removeSkill.mutateAsync(pendingRemoval);
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
