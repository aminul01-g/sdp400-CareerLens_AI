"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { skillsApi } from "@/lib/api/skills";
import type { TaxonomySearchResponse, UserSkill } from "@/lib/api/types";

export const skillKeys = {
  all: ["skills"] as const,
  taxonomy: (q: string, category?: string) => ["skills", "taxonomy", q, category ?? ""] as const,
  categories: ["skills", "taxonomy", "categories"] as const,
};

export function useUserSkills(filters?: { source?: string; category?: string }) {
  return useQuery({
    queryKey: [...skillKeys.all, "mine", filters?.source ?? "", filters?.category ?? ""],
    queryFn: () => skillsApi.list(filters),
  });
}

/** The catalogue's own categories, for the picker's category filter. */
export function useTaxonomyCategories() {
  return useQuery({
    queryKey: skillKeys.categories,
    queryFn: () => skillsApi.taxonomyCategories(),
    staleTime: 60_000,
  });
}

/** Alias-aware taxonomy search. Debounced by the caller, not here. */
export function useTaxonomySearch(params: { q?: string; category?: string; limit?: number }) {
  return useQuery({
    queryKey: skillKeys.taxonomy(params.q ?? "", params.category),
    queryFn: () => skillsApi.searchTaxonomy({ ...params, limit: params.limit ?? 20 }),
    enabled: (params.q ?? "").trim().length > 0 || Boolean(params.category),
    staleTime: 60_000,
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: skillKeys.all });
  void client.invalidateQueries({ queryKey: ["dashboard"] });
  void client.invalidateQueries({ queryKey: ["cv"] });
}

export function useAddSkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      skill_id: number;
      proficiency?: number;
      years_used?: number | null;
      last_used_at?: string | null;
    }) => skillsApi.add(input),
    onSuccess: () => invalidate(client),
  });
}

export function useUpdateSkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      skillId,
      ...payload
    }: {
      skillId: number;
      proficiency?: number;
      years_used?: number | null;
      last_used_at?: string | null;
      confirmed?: boolean;
    }) => skillsApi.update(skillId, payload),
    onSuccess: () => invalidate(client),
  });
}

export function useRemoveSkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (skillId: number) => skillsApi.remove(skillId),
    // No optimistic delete. A delete that appears to succeed and then fails is
    // worse than a 300 ms wait, because the user has already moved on.
    onSuccess: () => invalidate(client),
  });
}

export function useConfirmSkills() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      resume_upload_id?: number | null;
      skills: { skill_id: number; accepted: boolean; proficiency?: number }[];
    }) => skillsApi.confirm(input),
    onSuccess: () => invalidate(client),
  });
}

export type { UserSkill, TaxonomySearchResponse };
