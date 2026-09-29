import { apiFetch } from "./client";
import type { Certification, Page } from "./types";

export interface CertificationPayload {
  name: string;
  issuer: string;
  issued_on?: string | null;
  expires_on?: string | null;
  credential_url?: string | null;
}

export const certificationsApi = {
  list: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<Page<Certification>>("/certifications", query),
  create: (body: CertificationPayload) =>
    apiFetch.post<Certification>("/certifications", body),
  update: (id: number, body: Partial<CertificationPayload>) =>
    apiFetch.patch<Certification>(`/certifications/${id}`, body),
  remove: (id: number) => apiFetch.delete<void>(`/certifications/${id}`),
};
