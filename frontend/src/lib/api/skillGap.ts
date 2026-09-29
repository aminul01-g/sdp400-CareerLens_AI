import { apiFetch } from "./client";
import type { LearningPath, SkillGapResponse } from "./types";

export const skillGapApi = {
  gap: (jobRoleId: number) => apiFetch.get<SkillGapResponse>(`/skill-gap/${jobRoleId}`),
  /**
   * Optional feature. Returns 503 while `LLM_ENABLED=false` — the default — which
   * is a deliberate, distinct signal that the core gap report is independent of it.
   */
  learningPath: (jobRoleId: number) =>
    apiFetch.post<LearningPath>(`/skill-gap/${jobRoleId}/learning-path`),
};
