"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { certificationsApi, type CertificationPayload } from "@/lib/api/certifications";
import type { Certification } from "@/lib/api/types";

export const certificationKeys = { all: ["certifications"] as const };

export function useCertifications(page = 1) {
  return useQuery({
    queryKey: [...certificationKeys.all, page],
    queryFn: () => certificationsApi.list({ page, page_size: 50 }),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: certificationKeys.all });
  void client.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateCertification() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (body: CertificationPayload) => certificationsApi.create(body), onSuccess: () => invalidate(client) });
}

export function useUpdateCertification() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Partial<CertificationPayload>) => certificationsApi.update(id, body),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteCertification() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (id: number) => certificationsApi.remove(id), onSuccess: () => invalidate(client) });
}

export type { Certification };
