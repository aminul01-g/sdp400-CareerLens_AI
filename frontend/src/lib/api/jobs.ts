import { apiFetch } from "./client";
import type { FamilyCount, JobRole, JobRoleSummary, Page } from "./types";

export const jobsApi = {
  /** Public: no token required. A user must be able to browse roles. */
  list: (query?: { family?: string; q?: string; page?: number; page_size?: number }) =>
    apiFetch.get<Page<JobRoleSummary>>("/jobs", query),
  families: () => apiFetch.get<FamilyCount[]>("/jobs/families"),
  get: (id: number) => apiFetch.get<JobRole>(`/jobs/${id}`),
};
