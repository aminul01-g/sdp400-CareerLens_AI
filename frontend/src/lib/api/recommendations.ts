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

  /**
   * Say what the user thought of a recommended role.
   *
   * Idempotent: marking the same role again updates the record rather than
   * adding a second one, so one user cannot vote twice.
   */
  recordFeedback: (runId: number, jobRoleId: number, action: FeedbackAction) =>
    apiFetch.post<{ job_role_id: number; action: string; created_at: string }>(
      `/recommendations/runs/${runId}/roles/${jobRoleId}/feedback`,
      { action },
    ),
  /** What the caller said about the roles in a run. */
  feedback: (runId: number) =>
    apiFetch.get<Record<string, string>>(`/recommendations/runs/${runId}/feedback`),
};

/**
 * What a user said about a role.
 *
 * The first three are **interest**: what the user did with the shortlist.
 * The last three are **outcome**: what happened afterwards, reported by the
 * user. The community prior weights the second kind above the first, because
 * an interview is better evidence of a good match than a save is.
 */
export type FeedbackAction =
  | "saved"
  | "dismissed"
  | "interested"
  | "applied"
  | "interview"
  | "offer";

/** The actions that report an outcome rather than an opinion. */
export const OUTCOME_ACTIONS = ["applied", "interview", "offer"] as const;

/** How each outcome is labelled, in the order the buttons appear. */
export const OUTCOME_LABELS: Record<(typeof OUTCOME_ACTIONS)[number], string> = {
  applied: "I applied",
  interview: "Got an interview",
  offer: "Got an offer",
};
