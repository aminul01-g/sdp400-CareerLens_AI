"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi, type ProjectPayload } from "@/lib/api/projects";
import type { Project } from "@/lib/api/types";

export const projectKeys = { all: ["projects"] as const };

export function useProjects(page = 1) {
  return useQuery({
    queryKey: [...projectKeys.all, page],
    queryFn: () => projectsApi.list({ page, page_size: 50 }),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: projectKeys.all });
  void client.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateProject() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (body: ProjectPayload) => projectsApi.create(body), onSuccess: () => invalidate(client) });
}

export function useUpdateProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Partial<ProjectPayload>) => projectsApi.update(id, body),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteProject() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (id: number) => projectsApi.remove(id), onSuccess: () => invalidate(client) });
}

export type { Project };
