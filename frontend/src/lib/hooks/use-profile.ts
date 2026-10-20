"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileApi, type ProfilePayload } from "@/lib/api/profile";
import type { Profile } from "@/lib/api/types";

export const profileKeys = { all: ["profile"] as const };

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.all,
    queryFn: () => profileApi.get(),
    // GET /api/profile is get-or-create, so it never 404s for an authenticated user.
    staleTime: 30_000,
  });
}

export function useUpdateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfilePayload) => profileApi.update(payload),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: profileKeys.all });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => profileApi.delete(),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: profileKeys.all });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export type { Profile };
