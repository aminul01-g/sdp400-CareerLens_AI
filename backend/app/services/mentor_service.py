"""The AI career mentor.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The answer is grounded         The prompt carries the user's verified
                               record and nothing else. The record is
                               assembled by
                               :mod:`app.services.ai_context_service`, which
                               reads confirmed rows and stored engine
                               output
The answer admits ignorance    When the record does not contain what the
                               question needs, the response says so in
                               ``limitations`` and the prompt tells the model
                               to ask for the missing piece rather than
                               guess
The conversation stays small   Only the last few turns are sent, and the
                               whole window is capped, so a long chat does
                               not grow the request without bound
============================  ==========================================
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import prompts
from app.models.profile import Profile
from app.models.user import User
from app.schemas.ai import MentorAnswerRead, MentorAskRequest
from app.services import ai_context_service, groq_service

#: The number of recent exchanges the model is shown. Three exchanges is
#: enough for "what about the second one?" and short enough that the
#: request stays small.
CONVERSATION_TURNS = 6


def _language_for(db: Session, user: User, requested: str | None) -> str:
    """Which language to answer in.

    A per-request choice wins; otherwise the profile's stored preference; and
    English if neither is set. The choice changes the language of the
    explanation and nothing else.
    """
    if requested:
        return prompts.normalise_language(requested)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return prompts.normalise_language(profile.preferred_language)
    return "en"


def _context_used(facts: dict[str, Any]) -> list[str]:
    """A short, readable list of what the answer was grounded in.

    Shown in the interface so a learner can see which of their own records
    the answer used, rather than having to take it on trust.
    """
    used: list[str] = []
    skills = facts.get("skills") or []
    if skills:
        names = ", ".join(str(skill.get("name", "")) for skill in skills[:5])
        more = len(skills) - 5
        used.append(
            f"{len(skills)} confirmed skill{'s' if len(skills) != 1 else ''}"
            + (f" ({names}, +{more} more)" if more > 0 else f" ({names})")
        )
    projects = facts.get("projects") or []
    if projects:
        used.append(f"{len(projects)} project{'s' if len(projects) != 1 else ''}")
    education = facts.get("education") or []
    if education:
        used.append(f"{len(education)} education record{'s' if len(education) != 1 else ''}")
    work = facts.get("work_history") or []
    if work:
        used.append(f"{len(work)} confirmed role{'s' if len(work) != 1 else ''}")
    recommendations = facts.get("recommendations") or []
    if recommendations:
        top = recommendations[0]
        used.append(
            f"your latest shortlist (top match: {top.get('title', 'unknown')} "
            f"at {float(top.get('compatibility_score', 0)) * 100:.1f}%)"
        )
    target = facts.get("target_role")
    if isinstance(target, dict) and target:
        used.append(
            f"the gap report for {target.get('title', 'the selected role')} "
            f"({float(target.get('coverage', 0)) * 100:.1f}% coverage)"
        )
    return used


def _limitations(facts: dict[str, Any], question: str) -> list[str]:
    """What the record does not contain, stated plainly.

    The point is honesty, not completeness. A learner who asks "why did this
    role rank first?" and has never run the engine deserves to be told that
    rather than given a plausible story.
    """
    notes: list[str] = []
    lowered = question.lower()

    if not (facts.get("skills") or []):
        notes.append(
            "Your profile has no confirmed skills yet, so this answer is general "
            "rather than specific to you. Add your skills and it can be much more "
            "precise."
        )
    if not (facts.get("projects") or []):
        notes.append(
            "No projects are recorded on your profile, so I cannot point at work "
            "you have actually done."
        )
    if not (facts.get("recommendations") or []):
        notes.append(
            "You have not generated a recommendation run yet, so I cannot explain "
            "a ranking. Generate recommendations first and the engine's own "
            "numbers will be available to talk about."
        )
    if any(word in lowered for word in ("salary", "pay", "ctc", "package")):
        notes.append(
            "This application holds no salary data, so I cannot give you a figure "
            "for this role. Any number you see elsewhere about it is somebody "
            "else's estimate."
        )
    if any(word in lowered for word in ("my cv", "my resume", "my document")):
        notes.append(
            "Your CV text is not part of this conversation. Upload and analyse "
            "the CV, or use the CV advice tool, and the suggestions will be "
            "based on the document itself."
        )
    return notes


def ask(
    db: Session,
    user: User,
    request: MentorAskRequest,
) -> MentorAnswerRead:
    """Answer one question, grounded in the user's verified record."""
    # The deployment-level check comes first: a user on a deployment without a
    # provider should be told that, not told that a role does not exist.
    groq_service.require_provider()
    language = _language_for(db, user, request.language)
    facts = ai_context_service.build_facts(db, user, job_role_id=request.job_role_id)

    history = [
        {"role": turn.role, "content": turn.content}
        for turn in request.history[-CONVERSATION_TURNS:]
    ]
    messages = prompts.mentor_prompt(
        question=request.message,
        facts=facts,
        history=history,
        language=language,
    )
    answer = groq_service.run_chat(
        messages,
        temperature=0.6,
        reasoning_effort="medium",
        # The model's reasoning comes out of the same allowance as the answer,
        # so a tight cap truncates the reply rather than shortening it.
        max_completion_tokens=3000,
    )
    return MentorAnswerRead(
        answer=answer.strip(),
        generated_by=f"groq:{groq_service.provider_status().get('model', '')}",
        language=language,
        context_used=_context_used(facts),
        limitations=_limitations(facts, request.message),
    )
