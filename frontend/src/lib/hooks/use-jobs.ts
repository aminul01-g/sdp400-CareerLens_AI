"use client";

import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "@/lib/api/jobs";
import type { JobRoleSummary } from "@/lib/api/types";

export const jobKeys = {
  all: ["jobs"] as const,
  list: (family: string, q: string) => ["jobs", "list", family, q] as const,
  families: ["jobs", "families"] as const,
  detail: (id: number) => ["jobs", "detail", id] as const,
};

/** Public role browsing. A user must be able to see roles without a token. */
export function useJobRoles(params: { family?: string; q?: string; page?: number } = {}) {
  return useQuery({
    queryKey: jobKeys.list(params.family ?? "", params.q ?? ""),
    queryFn: () => jobsApi.list({ ...params, page_size: 100 }),
    staleTime: 5 * 60_000,
  });
}

export function useJobFamilies() {
  return useQuery({ queryKey: jobKeys.families, queryFn: () => jobsApi.families(), staleTime: 5 * 60_000 });
}

export type { JobRoleSummary };
