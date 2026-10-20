"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cvApi } from "@/lib/api/cv";
import type { ResumeUpload, UploadResponse } from "@/lib/api/types";

export const cvKeys = { all: ["cv"] as const };

export function useUploads(page = 1) {
  return useQuery({
    queryKey: [...cvKeys.all, page],
    queryFn: () => cvApi.list({ page, page_size: 20 }),
  });
}

export function useUploadCv() {
  const client = useQueryClient();
  return useMutation<UploadResponse, unknown, { file: File; onProgress?: (f: number) => void }>({
    mutationFn: ({ file, onProgress }) => cvApi.upload(file, onProgress),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: cvKeys.all });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteUpload() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => cvApi.remove(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: cvKeys.all });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export type { ResumeUpload, UploadResponse };
