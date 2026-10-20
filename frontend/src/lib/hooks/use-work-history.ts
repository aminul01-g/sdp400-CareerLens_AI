"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workHistoryApi } from "@/lib/api/profile";
import type { WorkHistoryEntry } from "@/lib/api/types";

export const workHistoryKeys = {
  all: ["work-history"] as const,
};

export function useWorkHistory() {
  return useQuery({
    queryKey: workHistoryKeys.all,
    queryFn: () => workHistoryApi.list(),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: workHistoryKeys.all });
  // The experience signal feeds the recommendation engine, so a changed work
  // history means the stored recommendations are out of date.
  void client.invalidateQueries({ queryKey: ["recommendations"] });
  void client.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useAddWorkHistory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      employer: string;
      title?: string | null;
      start_date?: string | null;
      end_date?: string | null;
    }) => workHistoryApi.add(input),
    onSuccess: () => invalidate(client),
  });
}

export function useUpdateWorkHistory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: number;
      employer?: string;
      title?: string | null;
      start_date?: string | null;
      end_date?: string | null;
    }) => workHistoryApi.update(id, body),
    onSuccess: () => invalidate(client),
  });
}

/** Accept a proposal the CV pipeline made. */
export function useConfirmWorkHistory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => workHistoryApi.confirm(id),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteWorkHistory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => workHistoryApi.remove(id),
    onSuccess: () => invalidate(client),
  });
}

export type { WorkHistoryEntry };
