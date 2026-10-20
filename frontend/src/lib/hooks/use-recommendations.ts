"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  recommendationsApi,
  type FeedbackAction,
} from "@/lib/api/recommendations";
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

/**
 * Record what the user thought of a role.
 *
 * The mutation invalidates the run so the card reflects the new state. It does
 * **not** regenerate the recommendations: the prior is applied at generation
 * time, and a regeneration would cost a full engine run and append a row to
 * the history for what is, from the user's point of view, a button press.
 */
export function useRecordFeedback(runId: number | null) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { jobRoleId: number; action: FeedbackAction }) =>
      recommendationsApi.recordFeedback(runId as number, input.jobRoleId, input.action),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: recommendationKeys.run(runId ?? 0) });
    },
  });
}

export { ApiError };
export type { RunSummary, RunDetail, FeedbackAction };
