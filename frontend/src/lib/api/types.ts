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
