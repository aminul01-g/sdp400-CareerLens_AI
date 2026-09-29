"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api/dashboard";

export const dashboardKeys = {
  summary: ["dashboard", "summary"] as const,
  completeness: ["dashboard", "completeness"] as const,
};

export function useDashboardSummary() {
  return useQuery({ queryKey: dashboardKeys.summary, queryFn: () => dashboardApi.summary() });
}

export function useProfileCompleteness() {
  return useQuery({ queryKey: dashboardKeys.completeness, queryFn: () => dashboardApi.completeness() });
}
