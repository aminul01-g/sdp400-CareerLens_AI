import { apiFetch } from "./client";
import type { Profile, WorkHistoryEntry } from "./types";

export interface ProfilePayload {
  headline?: string | null;
  career_goal?: string | null;
  bio?: string | null;
  location?: string | null;
  education_level?: string | null;
  years_experience?: number | null;
  seniority?: string | null;
  industry?: string | null;
  preferred_role_family?: string | null;
  links?: Record<string, string>;
}

export const workHistoryApi = {
  list: () => apiFetch.get<WorkHistoryEntry[]>("/work-history"),
  add: (body: {
    employer: string;
    title?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }) => apiFetch.post<WorkHistoryEntry>("/work-history", body),
  update: (
    id: number,
    body: {
      employer?: string;
      title?: string | null;
      start_date?: string | null;
      end_date?: string | null;
    },
  ) => apiFetch.patch<WorkHistoryEntry>(`/work-history/${id}`, body),
  /** Accept a role the CV pipeline proposed. */
  confirm: (id: number) => apiFetch.post<WorkHistoryEntry>(`/work-history/${id}/confirm`),
  remove: (id: number) => apiFetch.delete<void>(`/work-history/${id}`),
};

export const profileApi = {
  get: () => apiFetch.get<Profile>("/profile"),
  create: (body: ProfilePayload) => apiFetch.post<Profile>("/profile", body),
  update: (body: ProfilePayload) => apiFetch.patch<Profile>("/profile", body),
  delete: () => apiFetch.delete<void>("/profile"),
};
