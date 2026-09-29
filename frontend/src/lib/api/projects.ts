import { apiFetch } from "./client";
import type { Page, Project } from "./types";

export interface ProjectPayload {
  title: string;
  description: string;
  tech_stack?: string[];
  role?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  repo_url?: string | null;
  is_public?: boolean;
}

export const projectsApi = {
  list: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<Project>>("/projects", query),
  get: (id: number) => apiFetch.get<Project>(`/projects/${id}`),
  create: (body: ProjectPayload) => apiFetch.post<Project>("/projects", body),
  update: (id: number, body: Partial<ProjectPayload>) =>
    apiFetch.patch<Project>(`/projects/${id}`, body),
  remove: (id: number) => apiFetch.delete<void>(`/projects/${id}`),
};
