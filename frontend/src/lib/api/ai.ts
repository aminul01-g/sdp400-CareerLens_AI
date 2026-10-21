import { apiFetch } from "./client";
import type {
  AiLanguage,
  AiStatus,
  CvAdvice,
  InterviewExchange,
  InterviewQuestion,
  InterviewSession,
  InterviewSessionSummary,
  JobAnalysis,
  MentorAnswer,
  MentorTurn,
  Page,
  Roadmap,
  RoadmapSummary,
  RoadmapTask,
} from "./types";

/**
 * The AI layer's client.
 *
 * Every one of these routes is optional: on a deployment with no provider
 * configured they answer `503 feature_disabled`, and the interface shows an
 * honest "not available here" panel rather than a button that always fails.
 * `status()` exists so the interface can tell the difference *before* the
 * user presses anything.
 */
export const aiApi = {
  status: () => apiFetch.get<AiStatus>("/ai/status"),

  mentor: {
    ask: (body: {
      message: string;
      history?: MentorTurn[];
      language?: AiLanguage;
      job_role_id?: number;
    }) => apiFetch.post<MentorAnswer>("/ai/mentor/ask", body),
  },

  roadmaps: {
    list: (query?: { page?: number; page_size?: number }) =>
      apiFetch.get<Page<RoadmapSummary>>("/ai/roadmaps", query),
    generate: (body: {
      job_role_id: number;
      duration_weeks: 4 | 6;
      language?: AiLanguage;
    }) => apiFetch.post<Roadmap>("/ai/roadmaps", body),
    get: (id: number) => apiFetch.get<Roadmap>(`/ai/roadmaps/${id}`),
    updateTask: (
      id: number,
      taskKey: string,
      body: { is_complete?: boolean; notes?: string; portfolio_url?: string },
    ) => apiFetch.patch<RoadmapTask>(`/ai/roadmaps/${id}/tasks/${taskKey}`, body),
    remove: (id: number) => apiFetch.delete<void>(`/ai/roadmaps/${id}`),
  },

  jobAnalysis: {
    analyse: (body: {
      job_description?: string;
      job_role_id?: number;
      language?: AiLanguage;
    }) => apiFetch.post<JobAnalysis>("/ai/job-analysis", body),
  },

  cvAdvice: {
    advise: (body: {
      resume_upload_id?: number;
      job_role_id?: number;
      language?: AiLanguage;
      include_cover_letter?: boolean;
      cv_text?: string;
    }) => apiFetch.post<CvAdvice>("/ai/cv-advice", body),
  },

  interviews: {
    list: (query?: { page?: number; page_size?: number }) =>
      apiFetch.get<Page<InterviewSessionSummary>>("/ai/interviews", query),
    start: (body: {
      job_role_id?: number;
      job_description?: string;
      language?: AiLanguage;
      question_count?: number;
    }) => apiFetch.post<InterviewSession>("/ai/interviews", body),
    get: (id: number) => apiFetch.get<InterviewSession>(`/ai/interviews/${id}`),
    answer: (id: number, body: { answer: string; position?: number }) =>
      apiFetch.post<InterviewExchange>(`/ai/interviews/${id}/answers`, body),
    nextQuestion: (id: number) =>
      apiFetch.post<InterviewQuestion>(`/ai/interviews/${id}/next-question`),
    remove: (id: number) => apiFetch.delete<void>(`/ai/interviews/${id}`),
  },
};
