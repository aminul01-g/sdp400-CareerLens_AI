import { apiFetch } from "./client";
import type { DashboardSummary, ProfileCompleteness } from "./types";

export const dashboardApi = {
  summary: () => apiFetch.get<DashboardSummary>("/dashboard/summary"),
  completeness: () => apiFetch.get<ProfileCompleteness>("/dashboard/completeness"),
};
