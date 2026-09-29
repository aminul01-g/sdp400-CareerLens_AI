import { apiFetch } from "./client";
import type { Profile } from "./types";

export interface ProfilePayload {
  headline?: string | null;
  career_goal?: string | null;
  bio?: string | null;
  location?: string | null;
  education_level?: string | null;
  years_experience?: number | null;
  preferred_role_family?: string | null;
  links?: Record<string, string>;
}

export const profileApi = {
  get: () => apiFetch.get<Profile>("/profile"),
  create: (body: ProfilePayload) => apiFetch.post<Profile>("/profile", body),
  update: (body: ProfilePayload) => apiFetch.patch<Profile>("/profile", body),
  delete: () => apiFetch.delete<void>("/profile"),
};
