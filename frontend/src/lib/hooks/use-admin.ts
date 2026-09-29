"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, type JobRolePayload } from "@/lib/api/admin";
import type { UserRole } from "@/lib/api/types";

export const adminKeys = {
  overview: ["admin", "overview"] as const,
  users: ["admin", "users"] as const,
  jobs: (q: string, family: string, isActive: string) => ["admin", "jobs", q, family, isActive] as const,
  job: (id: number) => ["admin", "job", id] as const,
  taxonomy: (q: string, category: string) => ["admin", "taxonomy", q, category] as const,
  evaluation: ["admin", "evaluation"] as const,
  feedback: ["admin", "feedback"] as const,
};

export function useAdminOverview() {
  return useQuery({ queryKey: adminKeys.overview, queryFn: () => adminApi.overview() });
}

export function useAdminUsers(page = 1) {
  return useQuery({ queryKey: [...adminKeys.users, page], queryFn: () => adminApi.users({ page, page_size: 20 }) });
}

export function useAdminJobs(params: { q?: string; family?: string; is_active?: boolean; page?: number }) {
  return useQuery({
    queryKey: adminKeys.jobs(params.q ?? "", params.family ?? "", String(params.is_active ?? "")),
    queryFn: () => adminApi.listJobs({ ...params, page_size: 20 }),
  });
}

export function useAdminJob(id: number | null) {
  return useQuery({ queryKey: adminKeys.job(id ?? 0), queryFn: () => adminApi.getJob(id as number), enabled: id != null });
}

export function useAdminTaxonomy(params: { q?: string; category?: string }) {
  return useQuery({
    queryKey: adminKeys.taxonomy(params.q ?? "", params.category ?? ""),
    queryFn: () => adminApi.listTaxonomy({ ...params, page_size: 50 }),
  });
}

export function useEvaluation() {
  return useQuery({
    queryKey: adminKeys.evaluation,
    queryFn: () => adminApi.evaluation(),
    // The report is a committed artefact; re-fetching it on every mount would add
    // nothing and would make the chart disagree with the document if it did.
    staleTime: Infinity,
    retry: false,
  });
}

export function useAdminFeedback() {
  return useQuery({ queryKey: adminKeys.feedback, queryFn: () => adminApi.feedback() });
}

function invalidateAll(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: ["admin"] });
  void client.invalidateQueries({ queryKey: ["jobs"] });
}

export function useCreateJob() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (body: JobRolePayload) => adminApi.createJob(body), onSuccess: () => invalidateAll(client) });
}

export function useUpdateJob() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Partial<Omit<JobRolePayload, "skills">>) => adminApi.updateJob(id, body),
    onSuccess: () => invalidateAll(client),
  });
}

export function useReplaceJobSkills() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, skills }: { id: number; skills: { skill_id: number; weight: number }[] }) =>
      adminApi.replaceJobSkills(id, skills),
    onSuccess: () => invalidateAll(client),
  });
}

export function useDeleteJob() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (id: number) => adminApi.deleteJob(id), onSuccess: () => invalidateAll(client) });
}

export function useSetUserRole() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: { id: number; role: UserRole }) => adminApi.setUserRole(id, role),
    onSuccess: () => invalidateAll(client),
  });
}

export function useCreateTaxonomySkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; category: string; description?: string; aliases?: string[] }) => adminApi.createSkill(body),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin", "taxonomy"] }),
  });
}

export function useUpdateTaxonomySkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & { name?: string; category?: string; description?: string; aliases?: string[] }) =>
      adminApi.updateSkill(id, body),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin", "taxonomy"] }),
  });
}

export function useDeleteTaxonomySkill() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => adminApi.deleteSkill(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin", "taxonomy"] }),
  });
}
