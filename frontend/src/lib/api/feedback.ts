import { apiFetch } from "./client";

export const feedbackApi = {
  send: (body: { category?: string; message: string; rating?: number | null }) =>
    apiFetch.post<{ id: number; created_at: string }>("/feedback", body),
};
