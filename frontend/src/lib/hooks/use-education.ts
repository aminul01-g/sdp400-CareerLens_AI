"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { educationApi, type EducationPayload } from "@/lib/api/education";
import type { EducationRecord } from "@/lib/api/types";

export const educationKeys = { all: ["education"] as const };

export function useEducation(page = 1) {
  return useQuery({
    queryKey: [...educationKeys.all, page],
    queryFn: () => educationApi.list({ page, page_size: 50 }),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: educationKeys.all });
  void client.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateEducation() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (body: EducationPayload) => educationApi.create(body), onSuccess: () => invalidate(client) });
}

export function useUpdateEducation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Partial<EducationPayload>) => educationApi.update(id, body),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteEducation() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (id: number) => educationApi.remove(id), onSuccess: () => invalidate(client) });
}

export type { EducationRecord };
