/**
 * Shared API types.
 *
 * These are hand-maintained mirrors of the Pydantic response models. They are not
 * generated, so when the API changes a type can drift — which is why the UI never
 * trusts a type it has not actually received: every screen renders explicit
 * loading, empty, and error states, and every mutation surfaces the server's own
 * field errors rather than a client-side guess.
 */

export type UserRole = "user" | "admin";

export interface Page<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string | null;
}

export interface TokenResponse {
  user: User;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Profile {
  id: number;
  user_id: number;
  headline: string | null;
  career_goal: string | null;
  bio: string | null;
  location: string | null;
  education_level: string | null;
  years_experience: number | null;
  /** One of Entry / Junior / Mid / Senior / Lead / Principal, or null. */
  seniority: string | null;
  industry: string | null;
  preferred_role_family: string | null;
  links: Record<string, string>;
  /** The language the generated AI guidance is written in. */
  preferred_language: "en" | "bn";
  created_at?: string | null;
  updated_at?: string | null;
  skills_count: number;
  projects_count: number;
  education_count: number;
  certifications_count: number;
}

export type Proficiency = 1 | 2 | 3 | 4 | 5;

export interface Skill {
  id: number;
  name: string;
  slug: string;
  category: string;
  description: string | null;
  aliases: string[];
}

export interface UserSkill {
  skill_id: number;
  name: string;
  slug: string;
  category: string;
  proficiency: number;
  years_used: number | null;
  /** When the skill was last used. Null means "not stated", which is neutral. */
  last_used_at: string | null;
  source: "manual" | "cv_extracted";
  confirmed: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WorkHistoryEntry {
  id: number;
  employer: string;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  /** "manual" or "cv_extracted". */
  source: string;
  /** False for a proposal the user has not accepted yet. */
  confirmed: boolean;
  raw_text: string | null;
}

export interface TaxonomySearchResponse {
  total: number;
  query: string | null;
  category: string | null;
  items: Skill[];
}

export interface ConfirmResult {
  added: number;
  updated: number;
  skipped: number;
  declined: number;
  accepted: number;
  rejected: number[];
  details: { skill_id: number; name: string; accepted: boolean }[];
}

export interface Project {
  id: number;
  user_id: number;
  title: string;
  description: string;
  tech_stack: string[];
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  repo_url: string | null;
  is_public: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  unrecognised_tech: string[];
}

export interface EducationRecord {
  id: number;
  user_id: number;
  institution: string;
  degree: string;
  field_of_study: string | null;
  start_year: number | null;
  end_year: number | null;
  grade: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Certification {
  id: number;
  user_id: number;
  name: string;
  issuer: string;
  issued_on: string | null;
  expires_on: string | null;
  credential_url: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SkillWeight {
  skill_id: number;
  name: string;
  slug: string;
  category: string;
  weight: number;
}

export interface JobRole {
  id: number;
  title: string;
  slug: string;
  family: string;
  seniority: string | null;
  description: string;
  responsibilities: string[];
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  skills: SkillWeight[];
}

export interface JobRoleSummary {
  id: number;
  title: string;
  slug: string;
  family: string;
  seniority: string | null;
  description: string;
  is_active: boolean;
  required_skills_count: number;
}

export interface JobRoleAdminSummary extends JobRoleSummary {
  total_weight: number;
  updated_at?: string | null;
}

export interface FamilyCount {
  family: string;
  count: number;
}

export interface DetectedSkill {
  skill_id: number;
  canonical_name: string;
  slug: string;
  category: string;
  surface_form: string;
  occurrence_count: number;
  match_start: number | null;
  match_end: number | null;
  accepted: boolean;
  already_confirmed: boolean;
  /** The section of the CV the match was found in. */
  section: string | null;
  /** True when it was found in a section where the person declares their skills. */
  is_declared: boolean;
}

export interface Achievement {
  /** The sentence the claim was read from. */
  text: string;
  /** The quantity as it was written: "80%", "3x", "$2M", "400,000 rows". */
  metric: string;
  /** The numeric part of the quantity, when there is one. */
  value: number | null;
  /** What the quantity measures. */
  unit: "percent" | "multiple" | "currency" | "count" | "duration" | string;
  /** Whether the number went up, went down, or neither. */
  direction: "increase" | "decrease" | "neutral" | string;
  /**
   * Whether the sentence reads as the candidate's own work, the team's, or
   * does not say. A first-person pronoun, not a judgement.
   */
  attribution: "individual" | "team" | "unattributed" | string;
}

export interface ResumeUpload {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: "uploaded" | "extracted" | "confirmed" | "failed";
  error_message: string | null;
  created_at?: string | null;
  text_length: number | null;
  detected_skills: DetectedSkill[];
  /** The quantified claims the document makes. */
  achievements: Achievement[];
}

export interface UploadResponse {
  resume_upload_id: number;
  status: string;
  filename: string;
  size_bytes: number;
  text_length: number;
  page_count: number | null;
  detected_skills: DetectedSkill[];
  already_confirmed: string[];
  /** The jobs the experience section proposed. Proposals, not facts. */
  work_history: WorkHistoryEntry[];
  /** The quantified claims the document makes. Proposals, not facts. */
  achievements: Achievement[];
  message: string;
}

export interface SkillContribution {
  skill_id: number;
  name: string;
  weight: number;
  proficiency: number | null;
  category: string | null;
  contribution: number;
}

export interface RoleRecommendation {
  rank: number;
  job_role_id: number;
  title: string;
  slug: string;
  family: string;
  seniority: string | null;
  compatibility_pct: number;
  skill_coverage: number;
  tfidf_similarity: number;
  matched_skills: SkillContribution[];
  missing_skills: SkillContribution[];
  coverage_contribution: number;
  tfidf_contribution: number;
  /** The coverage the user declared, before recency and depth were applied. */
  declared_coverage: number;
  /** That coverage after the recency and depth adjustments. */
  signal_coverage: number;
  /** The multiplier for the distance between the user's level and the role's. */
  level_fit: number;
  /** The community signal for this role, in [-1, 1]. 0 when there is no evidence. */
  role_prior: number;
  /** How many observations the prior is based on. */
  feedback_samples: number;
}

export interface AuditEntry {
  id: number;
  actor_id: number | null;
  actor_email: string | null;
  /** A stable identifier: "job_role.updated", "auth.login_failed". */
  action: string;
  entity_type: string;
  entity_id: string | null;
  /** Prose for a human. Do not filter on it. */
  summary: string;
  changes: Record<string, unknown>;
  client_ip: string | null;
  peer_ip: string | null;
  request_id: string | null;
  created_at: string;
}

export interface RecommendationResponse {
  run_id: number;
  engine_version: string;
  weights: { skill_coverage: number; tfidf_similarity: number };
  generated_at: string;
  total_candidates: number;
  results: RoleRecommendation[];
}

export interface RunSummary {
  id: number;
  created_at: string;
  engine_version: string;
  total_candidates: number;
  top_role_id: number | null;
  top_role_title: string | null;
  top_compatibility: number | null;
  coverage_weight: number;
  tfidf_weight: number;
}

export interface RunDetail {
  id: number;
  created_at: string;
  engine_version: string;
  weights: { skill_coverage: number; tfidf_similarity: number };
  total_candidates: number;
  duration_ms: number | null;
  profile_snapshot: Record<string, unknown>;
  results: RoleRecommendation[];
}

export type Tier = "critical" | "important" | "desirable";

export interface GapMatchedSkill {
  skill_id: number;
  name: string;
  category: string | null;
  weight: number;
  proficiency: number;
  contribution: number;
}

export interface GapMissingSkill {
  skill_id: number;
  name: string;
  category: string | null;
  weight: number;
  tier: Tier;
}

export interface SkillGapResponse {
  job_role: {
    job_role_id: number;
    title: string;
    family: string;
    seniority: string | null;
    required_skills_count: number;
  };
  coverage: number;
  coverage_pct: number;
  required_count: number;
  matched_count: number;
  missing_count: number;
  matched: GapMatchedSkill[];
  missing: GapMissingSkill[];
  tiers: { critical: number; important: number; desirable: number };
  learning_path_available: boolean;
}

export interface LearningPath {
  job_role_id: number;
  job_role_title: string;
  generated_by: string;
  steps: {
    order: number;
    skill_id: number;
    skill_name: string;
    weight: number;
    tier: Tier;
    guidance: string;
  }[];
}

export interface DashboardSummary {
  skills_count: number;
  projects_count: number;
  education_count: number;
  certifications_count: number;
  resume_uploads_count: number;
  total_recommendation_runs: number;
  latest_run_at: string | null;
  top_role_id: number | null;
  top_role_title: string | null;
  top_compatibility_pct: number | null;
  member_since: string | null;
}

export interface OnboardingStep {
  key: string;
  label: string;
  completed: boolean;
  href: string;
  hint: string;
}

export interface ProfileCompleteness {
  score: number;
  completed_fields: number;
  total_fields: number;
  steps: OnboardingStep[];
  next_action: OnboardingStep | null;
}

export interface AdminOverview {
  role_count: number;
  active_role_count: number;
  skill_count: number;
  alias_count: number;
  user_count: number;
  recommendation_run_count: number;
  latest_run_at: string | null;
  families: { family: string; count: number }[];
  top_skills: { skill_id: number; name: string; category: string; role_count: number }[];
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string | null;
  last_login_at?: string | null;
  skills_count: number;
  projects_count: number;
}

/**
 * A stored feedback entry, as `GET /api/admin/feedback` returns it.
 *
 * There is deliberately no `user_id` here: the backend's read model omits it
 * ("an admin listing has no need for it"), so an admin sees what was said but
 * not who said it. Do not add the field to the type without adding it to
 * `FeedbackRead` first.
 */
export interface AdminFeedback {
  id: number;
  category: string;
  message: string;
  rating: number | null;
  created_at: string;
}

/**
 * One hand-labelled profile's measured result.
 *
 * `expected_role`, `top1_role` and the entries of `top3_roles` / `ranked_roles`
 * are **role slugs**, not titles — the harness records what it compared, and the
 * slug is the stable identity. `expected_rank` is null when the expected role
 * fell outside the ranked list.
 */
export interface EvaluationOutcome {
  id: string;
  name: string;
  expected_role: string;
  expected_family: string;
  top1_role: string;
  top3_roles: string[];
  ranked_roles: string[];
  expected_rank: number | null;
  top1_compatibility: number;
  expected_compatibility: number;
  coverage: number;
  tfidf_similarity: number;
  rationale: string;
  note: string;
}

/** One row of the coverage/TF-IDF weight sweep. */
export interface EvaluationSweepPoint {
  coverage_weight: number;
  tfidf_weight: number;
  top1_accuracy: number;
  top3_hit_rate: number;
  mean_reciprocal_rank: number;
  mean_compatibility_of_expected: number;
}

/**
 * The committed evaluation report, exactly as `GET /api/admin/evaluation`
 * returns it.
 *
 * This mirrors the payload built in `app/ml/evaluation/harness.py`, which is the
 * artefact of record. Two earlier assumptions were wrong and are corrected here:
 *
 * - The target is **flat** (`target_top3_hit_rate` / `meets_target`), not nested
 *   under a `target` object.
 * - `per_family` is a **dict keyed by family name**, not an array, so a chart
 *   has to flatten it first.
 *
 * There is no `top5_hit_rate` and no `environment` block: the harness does not
 * compute either. Top-5 is deliberately not derived in the UI — this page's
 * contract is that it never recomputes a metric, so that it cannot disagree with
 * `docs/evaluation_report.md`.
 */
export interface EvaluationReport {
  schema_version: string;
  /** ISO date the harness ran, e.g. `2026-09-30`. */
  generated_at: string;
  target_top3_hit_rate: number;
  weights: { coverage: number; tfidf: number };
  metrics: {
    n_profiles: number;
    top1_accuracy: number;
    top3_hit_rate: number;
    mean_reciprocal_rank: number;
    mean_compatibility_of_expected: number;
    component_means: {
      compatibility: number;
      skill_coverage: number;
      tfidf_similarity: number;
    };
  };
  meets_target: boolean;
  per_family: Record<
    string,
    {
      n: number;
      top1_accuracy: number;
      top3_hit_rate: number;
      mean_reciprocal_rank: number;
    }
  >;
  sweep: EvaluationSweepPoint[];
  /** The weighting the harness recommends, with the metrics it produced. */
  recommendation: EvaluationSweepPoint;
  /** Compatibility a meaningless ranking would score, for scale. */
  noise_floor: number;
  outcomes: EvaluationOutcome[];
}

/* ------------------------------------------------------------------ *
 * The AI layer.
 *
 * These mirror the Pydantic models in `backend/app/schemas/ai.py`. Two
 * conventions carry over from the backend and are worth stating here:
 *
 * - `language` chooses the language of a *generated explanation*. It never
 *   changes a skill name, a role title or a calculated score, so none of
 *   those fields has a language-specific variant.
 * - Every generated answer says which provider produced it (`generated_by`)
 *   and, where a number is shown, what that number measures.
 * ------------------------------------------------------------------ */

export type AiLanguage = "en" | "bn";

export interface AiStatus {
  enabled: boolean;
  model: string;
  features: string[];
  languages: AiLanguage[];
}

export interface MentorTurn {
  role: "user" | "assistant";
  content: string;
}

export interface MentorAnswer {
  answer: string;
  generated_by: string;
  language: AiLanguage;
  /** The verified records the answer was grounded in, by name. */
  context_used: string[];
  /** What the answer could not do because the record does not contain it. */
  limitations: string[];
}

export interface LearningResource {
  id: string;
  title: string;
  url: string;
  kind: string;
  summary: string;
}

export interface RoadmapTask {
  task_key: string;
  week: number;
  position: number;
  title: string;
  objective: string;
  activities: string[];
  deliverable: string;
  completion_criteria: string[];
  estimated_hours: number;
  skill_slug: string;
  resources: LearningResource[];
  portfolio_hint: string;
  is_complete: boolean;
  notes: string;
  portfolio_url: string;
  completed_at: string | null;
}

export interface PortfolioProject {
  title: string;
  problem_statement: string;
  required_technologies: string[];
  milestones: string[];
  expected_outputs: string[];
  evaluation_criteria: string[];
  demonstrates_skills: string[];
}

export interface Roadmap {
  id: number;
  job_role_id: number | null;
  job_role_title: string;
  title: string;
  duration_weeks: number;
  language: AiLanguage;
  generated_by: string;
  created_at: string;
  target_role: string;
  starting_profile: string;
  strengths: string[];
  skill_gaps: string[];
  learning_objectives: string[];
  tasks: RoadmapTask[];
  portfolio_project: PortfolioProject | null;
  portfolio_presentation: string[];
  total_estimated_hours: number;
  notes: string;
  gap_skills: string[];
  completed_tasks: number;
  total_tasks: number;
  progress_pct: number;
}

export interface RoadmapSummary {
  id: number;
  job_role_id: number | null;
  job_role_title: string;
  title: string;
  duration_weeks: number;
  language: AiLanguage;
  created_at: string;
  completed_tasks: number;
  total_tasks: number;
  progress_pct: number;
}

/**
 * How a requirement from a job description stands against the profile.
 *
 * Three states, not two. `no_evidence` means the profile does not record the
 * skill either way — which is *not* the same as the person not having it.
 */
export type RequirementStatus = "met" | "gap" | "no_evidence";

export interface AnalyzedRequirement {
  skill: string;
  importance: "required" | "preferred";
  evidence: string;
  normalized_skill: string;
  normalized_slug: string;
  status: RequirementStatus;
  proficiency: number | null;
  note: string;
}

export interface JobAnalysis {
  role_title: string;
  summary: string;
  generated_by: string;
  language: AiLanguage;
  /**
   * The coverage the *application* computed over the skills extracted from
   * this description. Not the official score for a knowledge-base role —
   * that is `official_compatibility_pct` below, and it is only present when
   * the request named a role.
   */
  coverage: number;
  coverage_pct: number;
  official_compatibility_pct: number | null;
  matched_count: number;
  gap_count: number;
  no_evidence_count: number;
  requirements: AnalyzedRequirement[];
  tools_and_technologies: string[];
  experience_requirement: string;
  education_requirement: string;
  responsibilities: string[];
  deliverables: string[];
  checklist: string[];
  limitations: string[];
  unrecognised_skills: string[];
}

export interface CvAdvice {
  generated_by: string;
  language: AiLanguage;
  effective_summary: string[];
  emphasise: string[];
  clarity_suggestions: string[];
  wording_suggestions: string[];
  project_suggestions: string[];
  job_specific_recommendations: string[];
  professional_summary: string;
  bullet_points: string[];
  cover_letter: string;
  /** What the user must supply before a stronger draft is possible. */
  needs_information: string[];
  disclaimer: string;
}

export type InterviewCategory =
  | "technical"
  | "problem_solving"
  | "project"
  | "behavioral"
  | "scenario"
  | "follow_up";

export interface InterviewQuestion {
  question: string;
  category: InterviewCategory;
  focus: string;
  difficulty: "basic" | "intermediate" | "advanced";
  skill_slugs: string[];
}

export interface RubricDimension {
  key: string;
  label: string;
  description: string;
  score: number;
  max_score: number;
  note: string;
}

export interface InterviewFeedback {
  strengths: string[];
  missed_points: string[];
  technical_inaccuracies: string[];
  clarity_improvements: string[];
  example_answer: string;
  further_practice: string[];
  dimensions: RubricDimension[];
  /**
   * An informal practice score out of the rubric's maximum. It measures how
   * the answer performed against the five dimensions listed and nothing else.
   */
  practice_score: number;
  max_practice_score: number;
  score_note: string;
}

export interface InterviewExchange {
  position: number;
  question: InterviewQuestion;
  answer: string;
  feedback: InterviewFeedback | null;
}

export interface InterviewSession {
  id: number;
  job_role_id: number | null;
  job_label: string;
  language: AiLanguage;
  created_at: string;
  rubric: RubricDimension[];
  exchanges: InterviewExchange[];
}

export interface InterviewSessionSummary {
  id: number;
  job_role_id: number | null;
  job_label: string;
  language: AiLanguage;
  created_at: string;
  answered_count: number;
  question_count: number;
  average_practice_score: number | null;
}
