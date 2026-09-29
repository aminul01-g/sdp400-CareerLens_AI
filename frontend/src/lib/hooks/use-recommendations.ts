"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { recommendationsApi } from "@/lib/api/recommendations";
import { ApiError } from "@/lib/api/config";
import type { RecommendationResponse, RunDetail, RunSummary } from "@/lib/api/types";

export const recommendationKeys = {
  all: ["recommendations"] as const,
  runs: ["recommendations", "runs"] as const,
  run: (id: number) => ["recommendations", "run", id] as const,
};

export function useRuns(page = 1) {
  return useQuery({
    queryKey: [...recommendationKeys.runs, page],
    queryFn: () => recommendationsApi.runs({ page, page_size: 20 }),
  });
}

/**
 * Generating recommendations is a mutation, never a query.
 *
 * A query would fire on mount, so simply opening the page would burn a full
 * engine run and append a row to the user's run history every time. The plan
 * requires this to be a deliberate, button-triggered action.
 */
export function useGenerateRecommendations() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { limit?: number; role_family?: string | null; min_score?: number | null }) =>
      recommendationsApi.generate(input),
    onSuccess: (data: RecommendationResponse) => {
      void client.setQueryData(recommendationKeys.run(data.run_id), data);
      void client.invalidateQueries({ queryKey: recommendationKeys.runs });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

/** Reads a *persisted* run. Never recomputes — stored history must not change. */
export function useRun(id: number | null) {
  return useQuery({
    queryKey: recommendationKeys.run(id ?? 0),
    queryFn: () => recommendationsApi.run(id as number),
    enabled: id != null,
  });
}

export { ApiError };
export type { RunSummary, RunDetail };
