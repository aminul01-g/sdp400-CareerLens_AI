import { apiFetch } from "./client";
import type {
  AdminOverview,
  AdminUser,
  EvaluationReport,
  JobRole,
  JobRoleAdminSummary,
  Page,
  Skill,
  UserRole,
} from "./types";

export interface RoleSkillInput {
  skill_id: number;
  weight: number;
}

export interface JobRolePayload {
  title: string;
  family: string;
  seniority?: string | null;
  description: string;
  responsibilities?: string[];
  is_active?: boolean;
  skills: RoleSkillInput[];
}

export const adminApi = {
  overview: () => apiFetch.get<AdminOverview>("/admin/overview"),
  users: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<AdminUser>>("/admin/users", query),
  setUserRole: (userId: number, role: UserRole) =>
    apiFetch.patch<AdminUser>(`/admin/users/${userId}/role`, { role }),

  listJobs: (query?: { q?: string; family?: string; is_active?: boolean; page?: number; page_size?: number }) =>
    apiFetch.get<Page<JobRoleAdminSummary>>("/admin/jobs", query),
  getJob: (id: number) => apiFetch.get<JobRole>(`/admin/jobs/${id}`),
  createJob: (body: JobRolePayload) => apiFetch.post<JobRole>("/admin/jobs", body),
  updateJob: (id: number, body: Partial<Omit<JobRolePayload, "skills">>) =>
    apiFetch.patch<JobRole>(`/admin/jobs/${id}`, body),
  /** Full replacement. A validation failure leaves the previous set intact. */
  replaceJobSkills: (id: number, skills: RoleSkillInput[]) =>
    apiFetch.put<JobRole>(`/admin/jobs/${id}/skills`, { skills }),
  deleteJob: (id: number) => apiFetch.delete<void>(`/admin/jobs/${id}`),

  listTaxonomy: (query?: { q?: string; category?: string; page?: number; page_size?: number }) =>
    apiFetch.get<Page<Skill>>("/admin/taxonomy", query),
  createSkill: (body: { name: string; category: string; description?: string; aliases?: string[] }) =>
    apiFetch.post<Skill>("/admin/taxonomy", body),
  updateSkill: (
    id: number,
    body: { name?: string; category?: string; description?: string; aliases?: string[] },
  ) => apiFetch.patch<Skill>(`/admin/taxonomy/${id}`, body),
  deleteSkill: (id: number) => apiFetch.delete<void>(`/admin/taxonomy/${id}`),

  feedback: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<{ id: number; user_id: number; category: string; message: string; rating: number | null; created_at: string }>>(
      "/admin/feedback",
      query,
    ),
  evaluation: () => apiFetch.get<EvaluationReport>("/admin/evaluation"),
};
