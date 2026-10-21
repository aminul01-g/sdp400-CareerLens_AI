"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import { aiApi } from "@/lib/api/ai";
import type {
  AiLanguage,
  AiStatus,
  InterviewExchange,
  InterviewQuestion,
  InterviewSession,
  InterviewSessionSummary,
  MentorTurn,
  Page,
  Roadmap,
  RoadmapSummary,
  RoadmapTask,
} from "@/lib/api/types";

const aiKeys = {
  all: ["ai"] as const,
  status: ["ai", "status"] as const,
  roadmaps: ["ai", "roadmaps"] as const,
  roadmap: (id: number) => ["ai", "roadmap", id] as const,
  interviews: ["ai", "interviews"] as const,
  interview: (id: number) => ["ai", "interview", id] as const,
};

/**
 * Whether the AI layer is available on this deployment.
 *
 * A query, not a mutation: it is a read of the deployment's configuration and
 * it must not fire a model call. `staleTime` is generous because the answer
 * cannot change while the page is open.
 */
export function useAiStatus(): UseQueryResult<AiStatus> {
  return useQuery({
    queryKey: aiKeys.status,
    queryFn: () => aiApi.status(),
    staleTime: 5 * 60_000,
    retry: false,
  });
}

/**
 * Ask the career mentor.
 *
 * A mutation, not a query: every call reaches the provider and costs money,
 * so it must only happen when the user asks.
 */
export function useAskMentor() {
  return useMutation({
    mutationFn: (body: {
      message: string;
      history?: MentorTurn[];
      language?: AiLanguage;
      job_role_id?: number;
    }) => aiApi.mentor.ask(body),
  });
}

export function useRoadmaps(): UseQueryResult<Page<RoadmapSummary>> {
  return useQuery({
    queryKey: aiKeys.roadmaps,
    queryFn: () => aiApi.roadmaps.list({ page_size: 50 }),
    staleTime: 30_000,
  });
}

export function useGenerateRoadmap() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      job_role_id: number;
      duration_weeks: 4 | 6;
      language?: AiLanguage;
    }) => aiApi.roadmaps.generate(body),
    onSuccess: (data) => {
      client.setQueryData(aiKeys.roadmap(data.id), data);
      void client.invalidateQueries({ queryKey: aiKeys.roadmaps });
    },
  });
}

export function useRoadmap(id: number | null): UseQueryResult<Roadmap> {
  return useQuery({
    queryKey: aiKeys.roadmap(id ?? 0),
    queryFn: () => aiApi.roadmaps.get(id as number),
    enabled: id != null,
  });
}

export function useUpdateRoadmapTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      roadmapId: number;
      taskKey: string;
      is_complete?: boolean;
      notes?: string;
      portfolio_url?: string;
    }) =>
      aiApi.roadmaps.updateTask(body.roadmapId, body.taskKey, {
        is_complete: body.is_complete,
        notes: body.notes,
        portfolio_url: body.portfolio_url,
      }),
    onSuccess: (task: RoadmapTask, variables) => {
      // Patch the cached plan in place so the progress bar moves immediately,
      // and refresh the list so the summary agrees with it.
      const key = aiKeys.roadmap(variables.roadmapId);
      client.setQueryData<Roadmap>(key, (previous) =>
        previous
          ? {
              ...previous,
              tasks: previous.tasks.map((item) =>
                item.task_key === task.task_key ? task : item,
              ),
              completed_tasks: previous.tasks.filter(
                (item) =>
                  item.task_key === task.task_key ? task.is_complete : item.is_complete,
              ).length,
            }
          : previous,
      );
      void client.invalidateQueries({ queryKey: aiKeys.roadmaps });
    },
  });
}

export function useDeleteRoadmap() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => aiApi.roadmaps.remove(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: aiKeys.roadmaps });
    },
  });
}

export function useJobAnalysis() {
  return useMutation({
    mutationFn: (body: {
      job_description?: string;
      job_role_id?: number;
      language?: AiLanguage;
    }) => aiApi.jobAnalysis.analyse(body),
  });
}

export function useCvAdvice() {
  return useMutation({
    mutationFn: (body: {
      resume_upload_id?: number;
      job_role_id?: number;
      language?: AiLanguage;
      include_cover_letter?: boolean;
      cv_text?: string;
    }) => aiApi.cvAdvice.advise(body),
  });
}

export function useInterviews(): UseQueryResult<Page<InterviewSessionSummary>> {
  return useQuery({
    queryKey: aiKeys.interviews,
    queryFn: () => aiApi.interviews.list({ page_size: 50 }),
    staleTime: 30_000,
  });
}

export function useInterview(id: number | null): UseQueryResult<InterviewSession> {
  return useQuery({
    queryKey: aiKeys.interview(id ?? 0),
    queryFn: () => aiApi.interviews.get(id as number),
    enabled: id != null,
  });
}

export function useStartInterview() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      job_role_id?: number;
      job_description?: string;
      language?: AiLanguage;
      question_count?: number;
    }) => aiApi.interviews.start(body),
    onSuccess: (session) => {
      client.setQueryData(aiKeys.interview(session.id), session);
      void client.invalidateQueries({ queryKey: aiKeys.interviews });
    },
  });
}

export function useSubmitAnswer() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { sessionId: number; answer: string; position?: number }) =>
      aiApi.interviews.answer(body.sessionId, {
        answer: body.answer,
        position: body.position,
      }),
    onSuccess: (exchange: InterviewExchange, variables) => {
      // Merge the assessed exchange back into the cached session so the
      // feedback appears where the question is.
      const key = aiKeys.interview(variables.sessionId);
      client.setQueryData<InterviewSession>(key, (previous) =>
        previous
          ? {
              ...previous,
              exchanges: previous.exchanges.map((item) =>
                item.position === exchange.position ? exchange : item,
              ),
            }
          : previous,
      );
      void client.invalidateQueries({ queryKey: aiKeys.interviews });
    },
  });
}

export function useNextQuestion() {
  return useMutation({
    mutationFn: (sessionId: number) => aiApi.interviews.nextQuestion(sessionId),
  });
}

export function useDeleteInterview() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => aiApi.interviews.remove(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: aiKeys.interviews });
    },
  });
}

export type { InterviewQuestion };
