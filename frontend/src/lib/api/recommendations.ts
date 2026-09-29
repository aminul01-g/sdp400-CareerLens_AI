import { apiFetch } from "./client";
import type { Page, RecommendationResponse, RunDetail, RunSummary } from "./types";

export const recommendationsApi = {
  /** Triggered by a button, never on mount, so opening the page costs nothing. */
  generate: (body: { limit?: number; role_family?: string | null; min_score?: number | null }) =>
    apiFetch.post<RecommendationResponse>("/recommendations", body),
  runs: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<RunSummary>>("/recommendations/runs", query),
  /** Reads a stored run. Never recomputes — history must not change under us. */
  run: (id: number) => apiFetch.get<RunDetail>(`/recommendations/runs/${id}`),
};
