import { apiFetch } from "./client";
import type { EducationRecord, Page } from "./types";

export interface EducationPayload {
  institution: string;
  degree: string;
  field_of_study?: string | null;
  start_year?: number | null;
  end_year?: number | null;
  grade?: string | null;
}

export const educationApi = {
  list: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<EducationRecord>>("/education", query),
  create: (body: EducationPayload) => apiFetch.post<EducationRecord>("/education", body),
  update: (id: number, body: Partial<EducationPayload>) =>
    apiFetch.patch<EducationRecord>(`/education/${id}`, body),
  remove: (id: number) => apiFetch.delete<void>(`/education/${id}`),
};
