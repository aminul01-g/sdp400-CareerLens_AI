import { apiFetch } from "./client";
import type { ConfirmResult, TaxonomySearchResponse, UserSkill } from "./types";

export const skillsApi = {
  list: (query?: { source?: string; category?: string }) =>
    apiFetch.get<UserSkill[]>("/skills", query),
  add: (body: { skill_id: number; proficiency?: number; years_used?: number | null }) =>
    apiFetch.post<UserSkill>("/skills", body),
  update: (skillId: number, body: { proficiency?: number; years_used?: number | null; confirmed?: boolean }) =>
    apiFetch.patch<UserSkill>(`/skills/${skillId}`, body),
  remove: (skillId: number) => apiFetch.delete<void>(`/skills/${skillId}`),
  /** Alias-aware: searching "sklearn" finds "Scikit-learn". */
  searchTaxonomy: (query: { q?: string; category?: string; limit?: number; offset?: number }) =>
    apiFetch.get<TaxonomySearchResponse>("/skills/taxonomy", query),
  /** The step that promotes staged CV detections into the user's profile. */
  confirm: (body: {
    resume_upload_id?: number | null;
    skills: { skill_id: number; accepted: boolean; proficiency?: number }[];
  }) => apiFetch.post<ConfirmResult>("/skills/confirm", body),
};
