"use client";

import { useQuery } from "@tanstack/react-query";
import { skillGapApi } from "@/lib/api/skillGap";

export const skillGapKeys = { gap: (id: number) => ["skill-gap", id] as const };

export function useSkillGap(jobRoleId: number | null) {
  return useQuery({
    queryKey: skillGapKeys.gap(jobRoleId ?? 0),
    queryFn: () => skillGapApi.gap(jobRoleId as number),
    enabled: jobRoleId != null,
  });
}
