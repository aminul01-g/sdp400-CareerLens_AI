import { API_BASE_URL, ApiError, TOKEN_KEY } from "./config";
import { apiFetch } from "./client";
import type { ResumeUpload, UploadResponse } from "./types";

export const cvApi = {
  upload: (file: File, onProgress?: (fraction: number) => void) =>
    new Promise<UploadResponse>((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/api/cv/upload`);
      const token = typeof window !== "undefined" ? window.localStorage.getItem(TOKEN_KEY) : null;
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
      };
      xhr.onload = () => {
        let payload: unknown;
        try {
          payload = JSON.parse(xhr.responseText);
        } catch {
          payload = undefined;
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(payload as UploadResponse);
        } else {
          const envelope = payload as { error?: { message?: string } } | undefined;
          // Reuse the shared ApiError so the CV page handles failures exactly
          // like every other screen, including the 415/413/422 distinctions.
          reject(
            new ApiError(
              xhr.status,
              envelope?.error?.message ?? `Upload failed with status ${xhr.status}`,
              payload,
            ),
          );
        }
      };
      xhr.onerror = () => reject(new Error("The upload could not reach the server."));
      xhr.send(form);
    }),
  list: (query?: { page?: number; page_size?: number }) =>
    apiFetch.get<{ total: number; page: number; page_size: number; items: ResumeUpload[] }>("/cv", query),
  get: (id: number) => apiFetch.get<ResumeUpload>(`/cv/${id}`),
  text: (id: number) => apiFetch.get<{ text: string; text_length: number }>(`/cv/${id}/text`),
  remove: (id: number) => apiFetch.delete<void>(`/cv/${id}`),
};
