"""The shapes the model provider is asked to produce, and the transformer that
makes them safe to ask for.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
Pydantic validates             Every structured feature has a model here, and
                               the service validates the provider's answer
                               against it *before* the answer is displayed or
                               written to the database. A shape the app did
                               not ask for is a shape the app refuses
Strict-mode compatible         :func:`to_groq_schema` rewrites Pydantic's
                               JSON Schema into the subset the provider's
                               strict mode accepts: every object closed, every
                               property required, no ``$defs`` references and
                               no validation keywords
No optionals                   The provider's models have no ``Optional``
                               field. A missing value is an empty string or
                               an empty list, which keeps the schema free of
                               ``anyOf`` and therefore free of the one
                               construct most likely to be rejected
============================  ==========================================

The fields here are the *provider's* vocabulary. Anything the application
computes — a coverage score, a tier, a canonical skill name — is deliberately
absent, because the application computes those and the model does not get to
overwrite them.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

#: JSON Schema keywords the provider's strict mode does not accept, or that
#: the application enforces itself in Pydantic anyway. Stripping them keeps
#: the request as small as the provider can accept.
_STRIPPED_KEYWORDS = frozenset(
    {
        "default",
        "title",
        "examples",
        "deprecated",
        "readOnly",
        "writeOnly",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "format",
    }
)


def _inline(node: Any, definitions: dict[str, Any]) -> Any:
    """Rewrite one schema node into the strict-mode subset.

    ``$defs`` are resolved and inlined rather than referenced. A reference is
    legal in the schema, but inlining removes a whole class of provider-side
    resolution differences, and the schemas here are small enough that the
    duplication costs nothing.
    """
    if isinstance(node, list):
        return [_inline(item, definitions) for item in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref = node["$ref"]
        name = ref.rsplit("/", 1)[-1]
        target = definitions.get(name)
        if target is None:
            # An unresolvable reference means the model definition and the
            # schema disagree, which is a programming error, not a provider
            # error. Fail loudly rather than sending a broken schema.
            raise ValueError(f"unresolvable schema reference: {ref}")
        resolved = _inline(target, definitions)
        siblings = {k: v for k, v in node.items() if k != "$ref"}
        if siblings:
            resolved = {**resolved, **_inline(siblings, definitions)}
        return resolved

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _STRIPPED_KEYWORDS:
            continue
        if key == "properties":
            out["properties"] = {
                name: _inline(sub, definitions) for name, sub in value.items()
            }
            continue
        if key == "$defs":
            continue
        out[key] = _inline(value, definitions)

    if out.get("type") == "object" or "properties" in out:
        properties = out.get("properties")
        if isinstance(properties, dict):
            # Strict mode requires both of these, and requires *every*
            # property to be listed as required. The application decides what
            # a missing value means, so "always present" is the honest shape.
            out["additionalProperties"] = False
            out["required"] = list(properties.keys())
    return out


def to_groq_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Render ``model`` as a JSON Schema the provider's strict mode accepts."""
    raw = model.model_json_schema()
    definitions = raw.get("$defs", {})
    schema = {key: value for key, value in raw.items() if key != "$defs"}
    rendered = _inline(schema, definitions)
    rendered.setdefault("type", "object")
    return rendered


class _Strict(BaseModel):
    """Base for the provider's output models."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Learning roadmap
# ---------------------------------------------------------------------------
class RoadmapTaskOutput(_Strict):
    """One task inside one week of the plan."""

    week: int = Field(description="Which week of the plan this task belongs to.")
    title: str = Field(description="A short imperative title for the task.")
    objective: str = Field(
        description="What the learner should be able to do after this task."
    )
    activities: list[str] = Field(
        description="Two to four concrete practice activities, most actionable first."
    )
    deliverable: str = Field(
        description="The artefact this task produces, e.g. a working script or a README."
    )
    completion_criteria: list[str] = Field(
        description="How the learner knows the task is finished. Each item must be checkable."
    )
    estimated_hours: float = Field(description="Realistic hours for a student or new graduate.")
    skill_name: str = Field(
        description=(
            "The name of the skill this task builds, written exactly as it appears in the "
            "list of missing skills. An empty string if the task is not tied to one skill. "
            "Write the name, not a slug — the application resolves it."
        )
    )
    resource_ids: list[str] = Field(
        description=(
            "Identifiers of learning resources chosen from the provided resource list. "
            "Only use identifiers that were given. An empty list if none apply."
        )
    )
    portfolio_hint: str = Field(
        description=(
            "How this task contributes to the portfolio project, or an empty string."
        )
    )


class PortfolioProjectOutput(_Strict):
    """The practical project that demonstrates the target role's skills."""

    title: str
    problem_statement: str = Field(
        description="The real problem this project solves and who it is for."
    )
    required_technologies: list[str]
    milestones: list[str] = Field(
        description="Ordered milestones, each a small shippable increment."
    )
    expected_outputs: list[str] = Field(
        description="What the finished repository or artefact contains."
    )
    evaluation_criteria: list[str] = Field(
        description="How the work would be judged, and what would make it fail."
    )
    demonstrates_skills: list[str] = Field(
        description=(
            "The names of the skills this project demonstrates, written exactly as they "
            "appear in the list of missing skills."
        )
    )


class RoadmapPlanOutput(_Strict):
    """The whole learning plan for one role."""

    target_role: str
    starting_profile: str = Field(
        description=(
            "A short, factual description of where the learner starts, drawn only "
            "from the provided profile."
        )
    )
    strengths: list[str] = Field(
        description="The learner's existing strengths, named from the provided profile."
    )
    skill_gaps: list[str] = Field(
        description="The missing skills, most important first, named exactly as provided."
    )
    learning_objectives: list[str] = Field(
        description="Prioritised learning objectives. The first one is the single most valuable thing to learn next."
    )
    tasks: list[RoadmapTaskOutput]
    portfolio_project: PortfolioProjectOutput
    portfolio_presentation: list[str] = Field(
        description="How to present the finished work on GitHub or a personal portfolio."
    )
    total_estimated_hours: float = Field(
        description="Total realistic hours across the whole plan."
    )
    notes: str = Field(
        description=(
            "Anything the learner should know before starting, including honest "
            "limitations of the plan. An empty string if there is nothing to add."
        )
    )


# ---------------------------------------------------------------------------
# Job description analysis
# ---------------------------------------------------------------------------
class ExtractedRequirementOutput(_Strict):
    """One requirement found in a job description."""

    skill: str = Field(
        description=(
            "The skill or technology, written the way the job description writes it. "
            "Do not rename it and do not expand abbreviations."
        )
    )
    importance: Literal["required", "preferred"]
    evidence: str = Field(
        description=(
            "The phrase from the job description that this requirement came from."
        )
    )


class JobAnalysisOutput(_Strict):
    """The structured reading of one job description."""

    role_title: str = Field(
        description="The role's title, as the description states it. If none is stated, say 'Unspecified role'."
    )
    summary: str = Field(
        description="Two or three sentences on what this role actually does."
    )
    required_skills: list[ExtractedRequirementOutput]
    preferred_skills: list[ExtractedRequirementOutput]
    tools_and_technologies: list[str]
    experience_requirement: str = Field(
        description="The stated experience requirement, or an empty string if the description does not state one."
    )
    education_requirement: str = Field(
        description="The stated education requirement, or an empty string if the description does not state one."
    )
    responsibilities: list[str]
    deliverables: list[str] = Field(
        description="What the person in this role is expected to produce, or an empty list if the description does not say."
    )
    limitations: list[str] = Field(
        description=(
            "What the description does not say that a candidate would need. "
            "An empty list if the description is complete enough to analyse."
        )
    )


# ---------------------------------------------------------------------------
# CV advice
# ---------------------------------------------------------------------------
class CvAdviceOutput(_Strict):
    """Truthful suggestions for one CV."""

    effective_summary: list[str] = Field(
        description="What this CV already communicates well, citing what is in it."
    )
    emphasise: list[str] = Field(
        description=(
            "Skills, projects or achievements from the CV that deserve more emphasis, "
            "and why, referring to them by name."
        )
    )
    clarity_suggestions: list[str]
    wording_suggestions: list[str]
    project_suggestions: list[str] = Field(
        description="How to describe the projects and technical contributions more effectively."
    )
    job_specific_recommendations: list[str] = Field(
        description=(
            "How to foreground the genuine experience that matches the target role. "
            "An empty list when no job description was supplied."
        )
    )
    professional_summary: str = Field(
        description=(
            "A rewritten professional summary, using only facts that appear in the CV "
            "or the profile. No years of experience, employer, credential or metric "
            "that is not in the source."
        )
    )
    bullet_points: list[str] = Field(
        description=(
            "Draft bullet points for the CV's projects or experience, each built only "
            "from facts already in the CV."
        )
    )
    cover_letter: str = Field(
        description=(
            "A cover-letter draft for the target role, using only facts already in the "
            "CV and profile. An empty string when no cover letter was requested."
        )
    )
    needs_information: list[str] = Field(
        description=(
            "Questions the user must answer before a stronger draft is possible, "
            "each naming what is missing. An empty list if nothing is missing."
        )
    )


# ---------------------------------------------------------------------------
# Mock interview
# ---------------------------------------------------------------------------
class InterviewQuestionOutput(_Strict):
    """One interview question."""

    question: str
    category: Literal[
        "technical",
        "problem_solving",
        "project",
        "behavioral",
        "scenario",
        "follow_up",
    ]
    focus: str = Field(
        description="What this question is actually assessing, in one sentence."
    )
    difficulty: Literal["basic", "intermediate", "advanced"]
    skill_slugs: list[str] = Field(
        description=(
            "The skill slugs this question relates to, taken from the provided list. "
            "An empty list if it is a general question."
        )
    )


class InterviewQuestionsOutput(_Strict):
    """A list of interview questions.

    The provider's strict mode constrains an *object*, so a bare list is
    wrapped rather than sent on its own.
    """

    questions: list[InterviewQuestionOutput]


class RubricRatingsOutput(_Strict):
    """The five rubric dimensions, each scored by the model.

    The application owns the rubric: it defines the dimensions, stores them
    with the session, and does the arithmetic. The model only reports a
    judgement per dimension, and every judgement is still checked against
    the 0-5 range before it is accepted.
    """

    relevance: int
    correctness: int
    completeness: int
    reasoning: int
    clarity: int


class InterviewFeedbackOutput(_Strict):
    """Structured feedback on one interview answer."""

    strengths: list[str] = Field(
        description="What the answer did well, referring to what the candidate actually said."
    )
    missed_points: list[str] = Field(
        description="Important aspects the answer did not cover."
    )
    technical_inaccuracies: list[str] = Field(
        description=(
            "Statements in the answer that are technically wrong. An empty list if "
            "none were identified."
        )
    )
    clarity_improvements: list[str]
    example_answer: str = Field(
        description=(
            "A stronger version of the answer, or a clear outline of one. It must be "
            "something the candidate could genuinely say."
        )
    )
    further_practice: list[str] = Field(
        description="Specific topics, exercises or resources to practise next."
    )
    ratings: RubricRatingsOutput
    dimension_notes: list[str] = Field(
        description=(
            "One short line per rubric dimension explaining the score that was given, "
            "so the score is never a bare number."
        )
    )


#: The rubric, defined in code so a score is reproducible and auditable. The
#: same definition is stored with every interview session.
RUBRIC_DIMENSIONS: tuple[dict[str, str], ...] = (
    {
        "key": "relevance",
        "label": "Relevance",
        "description": "Does the answer address the question that was asked?",
    },
    {
        "key": "correctness",
        "label": "Correctness",
        "description": "Is what was said technically accurate?",
    },
    {
        "key": "completeness",
        "label": "Completeness",
        "description": "Does the answer cover the important parts of the question?",
    },
    {
        "key": "reasoning",
        "label": "Reasoning",
        "description": "Is the reasoning visible, structured and sound?",
    },
    {
        "key": "clarity",
        "label": "Clarity",
        "description": "Is the answer easy to follow and well organised?",
    },
)

#: The maximum a single dimension can score, and the maximum overall.
RUBRIC_MAX_PER_DIMENSION = 5
RUBRIC_MAX_TOTAL = RUBRIC_MAX_PER_DIMENSION * len(RUBRIC_DIMENSIONS)
