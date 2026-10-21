"""The AI layer's request and response schemas.

Three ideas run through this file.

**The language is not the data.** ``language`` chooses the language of a
generated explanation. It never changes a skill's canonical name, a role's
title, or any calculated number. The schemas that carry those values have no
language-specific variant of themselves.

**Every generated answer is labelled.** A response says which provider
produced it (``generated_by``) and, where a number is shown, what that number
measures. A learner should never be able to mistake a practice score for a
prediction of hiring.

**A missing fact is not a fact.** The CV advice carries a ``needs_information``
list, and the job analysis separates a skill the user has from a skill the
user has never written down. Both exist so the interface can say "we do not
know" instead of guessing.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.llm import RUBRIC_MAX_PER_DIMENSION, RUBRIC_MAX_TOTAL

#: The maximum length of a pasted job description. Long enough for a real
#: posting, short enough that the provider is never asked to read a novel.
MAX_JOB_DESCRIPTION_LENGTH = 20_000

#: The maximum length of one question to the mentor.
MAX_QUESTION_LENGTH = 2_000

#: The maximum length of a pasted CV excerpt.
MAX_CV_EXCERPT_LENGTH = 20_000

#: The maximum number of interview questions generated at once.
MAX_QUESTION_COUNT = 10

Language = Literal["en", "bn"]


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
class AiStatusRead(BaseModel):
    """``GET /api/ai/status``.

    What the interface is allowed to know about the provider: whether the
    feature is on, and which model is answering. Never the key.
    """

    enabled: bool
    model: str = ""
    features: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en", "bn"])


# ---------------------------------------------------------------------------
# Career mentor
# ---------------------------------------------------------------------------
class MentorTurn(BaseModel):
    """One turn of the conversation, as the client remembers it."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role: Literal["user", "assistant"] = "user"
    content: str = Field(default="", max_length=MAX_QUESTION_LENGTH)


class MentorAskRequest(BaseModel):
    """``POST /api/ai/mentor/ask``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        description="The question to ask.",
    )
    #: The recent conversation. The server keeps only the last few turns, so
    #: the client may send more without the request growing without bound.
    history: list[MentorTurn] = Field(default_factory=list, max_length=40)
    language: Language | None = Field(
        default=None, description="Overrides the profile's language for this question."
    )
    job_role_id: int | None = Field(
        default=None, ge=1, description="Focus the answer on one role from the knowledge base."
    )

    @field_validator("history")
    @classmethod
    def _bound_history(cls, value: list[MentorTurn]) -> list[MentorTurn]:
        return value[-12:]


class MentorAnswerRead(BaseModel):
    """The mentor's answer."""

    answer: str
    generated_by: str
    language: Language = "en"
    #: The verified records the answer was grounded in, by name. Shown so the
    #: learner can see which of their own facts the answer used.
    context_used: list[str] = Field(default_factory=list)
    #: What the answer could not do because the record does not contain it.
    limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Learning roadmap
# ---------------------------------------------------------------------------
class RoadmapGenerateRequest(BaseModel):
    """``POST /api/ai/roadmaps``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    job_role_id: int = Field(..., ge=1, description="The role to plan for.")
    duration_weeks: Literal[4, 6] = 4
    language: Language | None = None


class LearningResourceRead(BaseModel):
    """A verified learning resource. The URL comes from the registry."""

    id: str
    title: str
    url: str
    kind: str
    summary: str = ""


class RoadmapTaskRead(BaseModel):
    """One task, with the learner's progress on it."""

    task_key: str
    week: int
    position: int
    title: str
    objective: str = ""
    activities: list[str] = Field(default_factory=list)
    deliverable: str = ""
    completion_criteria: list[str] = Field(default_factory=list)
    estimated_hours: float = 0.0
    skill_slug: str = ""
    resources: list[LearningResourceRead] = Field(default_factory=list)
    portfolio_hint: str = ""
    is_complete: bool = False
    notes: str = ""
    portfolio_url: str = ""
    completed_at: str | None = None


class PortfolioProjectRead(BaseModel):
    """The practical project that demonstrates the target role's skills."""

    title: str
    problem_statement: str = ""
    required_technologies: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    demonstrates_skills: list[str] = Field(default_factory=list)


class RoadmapRead(BaseModel):
    """``GET /api/ai/roadmaps/{id}`` and the response of a generation."""

    id: int
    job_role_id: int | None = None
    job_role_title: str = ""
    title: str
    duration_weeks: int
    language: Language = "en"
    generated_by: str
    created_at: str
    target_role: str = ""
    starting_profile: str = ""
    strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    tasks: list[RoadmapTaskRead] = Field(default_factory=list)
    portfolio_project: PortfolioProjectRead | None = None
    portfolio_presentation: list[str] = Field(default_factory=list)
    total_estimated_hours: float = 0.0
    notes: str = ""
    #: The skills the engine reported as missing when the plan was made.
    gap_skills: list[str] = Field(default_factory=list)
    completed_tasks: int = 0
    total_tasks: int = 0
    progress_pct: float = 0.0


class RoadmapSummaryRead(BaseModel):
    """One row in the roadmap list."""

    id: int
    job_role_id: int | None = None
    job_role_title: str = ""
    title: str
    duration_weeks: int
    language: Language = "en"
    created_at: str
    completed_tasks: int = 0
    total_tasks: int = 0
    progress_pct: float = 0.0


class RoadmapTaskUpdate(BaseModel):
    """``PATCH /api/ai/roadmaps/{id}/tasks/{task_key}``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    is_complete: bool | None = None
    notes: Annotated[str, Field(max_length=4_000)] | None = None
    portfolio_url: Annotated[str, Field(max_length=600)] | None = None


# ---------------------------------------------------------------------------
# Job description analysis
# ---------------------------------------------------------------------------
class JobAnalysisRequest(BaseModel):
    """``POST /api/ai/job-analysis``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    job_description: str = Field(
        default="",
        max_length=MAX_JOB_DESCRIPTION_LENGTH,
        description="A pasted job description.",
    )
    job_role_id: int | None = Field(
        default=None,
        ge=1,
        description="A role from the knowledge base, to compare the description against.",
    )
    language: Language | None = None

    @field_validator("job_description")
    @classmethod
    def _bound_description(cls, value: str) -> str:
        return value.strip()


class AnalyzedRequirementRead(BaseModel):
    """One requirement, with the application's own reading of it."""

    #: The skill as the job description wrote it.
    skill: str
    importance: Literal["required", "preferred"]
    evidence: str = ""
    #: The canonical skill the application resolved it to, when the taxonomy
    #: knows it. Empty when it does not — and that is not a failure.
    normalized_skill: str = ""
    normalized_slug: str = ""
    #: ``met``, ``gap`` or ``no_evidence``. See the module docstring.
    status: Literal["met", "gap", "no_evidence"] = "no_evidence"
    #: The user's proficiency, when the status is ``met``.
    proficiency: int | None = None
    #: The reason for the status, in words.
    note: str = ""


class JobAnalysisRead(BaseModel):
    """``POST /api/ai/job-analysis``."""

    role_title: str
    summary: str = ""
    generated_by: str
    language: Language = "en"
    #: The compatibility the *application* computed over the skills extracted
    #: from this description. Not the official score for a knowledge-base
    #: role, and labelled as such in the interface.
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    #: The official score, when the request was about a knowledge-base role.
    official_compatibility_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    matched_count: int = 0
    gap_count: int = 0
    no_evidence_count: int = 0
    requirements: list[AnalyzedRequirementRead] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    experience_requirement: str = ""
    education_requirement: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    #: A prioritised preparation checklist.
    checklist: list[str] = Field(default_factory=list)
    #: What the description did not say that a candidate would need.
    limitations: list[str] = Field(default_factory=list)
    #: Skills the description named that the taxonomy does not know. They are
    #: reported rather than silently dropped.
    unrecognised_skills: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CV advice
# ---------------------------------------------------------------------------
class CvAdviceRequest(BaseModel):
    """``POST /api/ai/cv-advice``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    resume_upload_id: int | None = Field(
        default=None, ge=1, description="The analysed CV to review."
    )
    job_role_id: int | None = Field(
        default=None, ge=1, description="A role to tailor the advice to."
    )
    language: Language | None = None
    include_cover_letter: bool = False
    #: A CV pasted directly, when the user has not uploaded one.
    cv_text: str = Field(default="", max_length=MAX_CV_EXCERPT_LENGTH)


class CvAdviceRead(BaseModel):
    """``POST /api/ai/cv-advice``."""

    generated_by: str
    language: Language = "en"
    effective_summary: list[str] = Field(default_factory=list)
    emphasise: list[str] = Field(default_factory=list)
    clarity_suggestions: list[str] = Field(default_factory=list)
    wording_suggestions: list[str] = Field(default_factory=list)
    project_suggestions: list[str] = Field(default_factory=list)
    job_specific_recommendations: list[str] = Field(default_factory=list)
    professional_summary: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    cover_letter: str = ""
    #: What the user must supply before a stronger draft is possible.
    needs_information: list[str] = Field(default_factory=list)
    #: Always present. The application does not claim ATS compatibility or
    #: hiring success, and the interface says so.
    disclaimer: str = (
        "These suggestions help you describe your own experience more clearly. "
        "They do not guarantee that any application system will accept the CV, "
        "and they do not change what you have actually done. Check every "
        "suggested line against the truth of your own record before you use it."
    )


# ---------------------------------------------------------------------------
# Mock interview
# ---------------------------------------------------------------------------
class InterviewStartRequest(BaseModel):
    """``POST /api/ai/interviews``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    job_role_id: int | None = Field(default=None, ge=1)
    job_description: str = Field(default="", max_length=MAX_JOB_DESCRIPTION_LENGTH)
    language: Language | None = None
    question_count: int = Field(default=6, ge=1, le=MAX_QUESTION_COUNT)


class InterviewQuestionRead(BaseModel):
    """One question, as it was asked."""

    question: str
    category: Literal[
        "technical",
        "problem_solving",
        "project",
        "behavioral",
        "scenario",
        "follow_up",
    ]
    focus: str = ""
    difficulty: Literal["basic", "intermediate", "advanced"] = "intermediate"
    skill_slugs: list[str] = Field(default_factory=list)


class RubricDimensionRead(BaseModel):
    """One rubric dimension and what it measures."""

    key: str
    label: str
    description: str
    score: int = 0
    max_score: int = RUBRIC_MAX_PER_DIMENSION
    note: str = ""


class InterviewFeedbackRead(BaseModel):
    """The feedback on one answer."""

    strengths: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)
    technical_inaccuracies: list[str] = Field(default_factory=list)
    clarity_improvements: list[str] = Field(default_factory=list)
    example_answer: str = ""
    further_practice: list[str] = Field(default_factory=list)
    dimensions: list[RubricDimensionRead] = Field(default_factory=list)
    #: The informal practice score, out of the rubric's maximum.
    practice_score: int = 0
    max_practice_score: int = RUBRIC_MAX_TOTAL
    #: Always present, and says what the number is.
    score_note: str = (
        "This is an informal practice score from the rubric below, not a "
        "prediction of hiring success. It measures how your answer performed "
        "against the five dimensions listed, and nothing else."
    )


class InterviewAnswerRequest(BaseModel):
    """``POST /api/ai/interviews/{id}/answers``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    answer: str = Field(default="", max_length=8_000)
    #: Which question is being answered. Defaults to the next unanswered one.
    position: int | None = Field(default=None, ge=1)


class InterviewExchangeRead(BaseModel):
    """One question, the answer and the feedback."""

    position: int
    question: InterviewQuestionRead
    answer: str = ""
    feedback: InterviewFeedbackRead | None = None


class InterviewSessionRead(BaseModel):
    """``GET /api/ai/interviews/{id}``."""

    id: int
    job_role_id: int | None = None
    job_label: str
    language: Language = "en"
    created_at: str
    rubric: list[RubricDimensionRead] = Field(default_factory=list)
    exchanges: list[InterviewExchangeRead] = Field(default_factory=list)


class InterviewSessionSummaryRead(BaseModel):
    """One row in the session list."""

    id: int
    job_role_id: int | None = None
    job_label: str
    language: Language = "en"
    created_at: str
    answered_count: int = 0
    question_count: int = 0
    average_practice_score: int | None = None
