"""The mock interview simulator.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The rubric is the application's  The five dimensions, their descriptions and
                               the maximum score are defined in
                               :mod:`app.schemas.llm` and stored with the
                               session. The model reports a rating per
                               dimension; the total is computed here
A rating is checked             A rating outside 0-5 is clamped and
                               rejected by the schema, so a model cannot
                               produce a 9 and have it displayed
The score is labelled            Every response carries ``score_note``,
                               which says what the number measures and
                               that it is a practice score, not a prediction
A session is private            Every read and write is scoped by owner in
                               the query, so another user's session id is a
                               404
============================  ==========================================
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, UnprocessableError
from app.ml import prompts
from app.models.interview import InterviewExchange, InterviewSession
from app.models.profile import Profile
from app.models.user import User
from app.schemas.ai import (
    InterviewAnswerRequest,
    InterviewExchangeRead,
    InterviewFeedbackRead,
    InterviewQuestionRead,
    InterviewSessionRead,
    InterviewSessionSummaryRead,
    InterviewStartRequest,
    RubricDimensionRead,
)
from app.schemas.llm import (
    RUBRIC_DIMENSIONS,
    RUBRIC_MAX_PER_DIMENSION,
    RUBRIC_MAX_TOTAL,
    InterviewFeedbackOutput,
    InterviewQuestionOutput,
    InterviewQuestionsOutput,
)
from app.services import ai_context_service, groq_service

logger = logging.getLogger("app.services.interview")

#: How many questions a session holds at once.
MAX_QUESTIONS = 10

#: The smallest answer worth assessing. A single word is not an answer, and
#: assessing it would produce a score with no meaning.
MIN_ANSWER_CHARS = 20


def _rubric_document() -> list[dict[str, str]]:
    """The rubric, as it is stored with a session."""
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "description": item["description"],
            "max_score": str(RUBRIC_MAX_PER_DIMENSION),
        }
        for item in RUBRIC_DIMENSIONS
    ]


def _rubric_dimensions() -> list[RubricDimensionRead]:
    return [
        RubricDimensionRead(
            key=item["key"],
            label=item["label"],
            description=item["description"],
            score=0,
            max_score=RUBRIC_MAX_PER_DIMENSION,
        )
        for item in RUBRIC_DIMENSIONS
    ]


def _resolve_language(db: Session, user: User, requested: str | None) -> str:
    if requested:
        return prompts.normalise_language(requested)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return prompts.normalise_language(profile.preferred_language)
    return "en"


def _load_session(db: Session, user: User, session_id: int) -> InterviewSession:
    """One session, scoped by owner in the query."""
    session = db.scalar(
        select(InterviewSession)
        .options(selectinload(InterviewSession.exchanges))
        .where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user.id,
        )
    )
    if session is None:
        raise NotFoundError("That interview session does not exist.")
    return session


def start(
    db: Session,
    user: User,
    request: InterviewStartRequest,
) -> InterviewSessionRead:
    """Begin an interview and generate its opening questions."""
    groq_service.require_provider()
    description = request.job_description.strip()
    if request.job_role_id is None and len(description) < 120:
        raise UnprocessableError(
            "Choose a role from the knowledge base, or paste a full job "
            "description, so the questions have something to be about.",
            code="insufficient_job_description",
        )

    language = _resolve_language(db, user, request.language)
    facts = ai_context_service.build_facts(db, user, job_role_id=request.job_role_id)
    requirements = (
        ai_context_service.role_requirements(db, request.job_role_id)
        if request.job_role_id is not None
        else []
    )
    role_title = "this role"
    job_label = "Custom job description"
    if request.job_role_id is not None:
        target = facts.get("target_role")
        if isinstance(target, dict):
            role_title = str(target.get("title", "this role"))
            job_label = role_title
    elif description:
        job_label = "Custom job description"

    count = max(1, min(request.question_count, MAX_QUESTIONS))
    messages = prompts.interview_questions_prompt(
        role_title=role_title,
        requirements=requirements,
        facts=facts,
        job_description=description,
        count=count,
        language=language,
    )
    generated = groq_service.run_structured(
        messages,
        InterviewQuestionsOutput,
        schema_name="interview_questions",
        reasoning_effort="medium",
        max_completion_tokens=4000,
    )
    questions = generated.questions
    if not questions:
        raise UnprocessableError(
            "The interview could not be prepared. Please try again.",
            code="interview_unavailable",
        )

    session = InterviewSession(
        user_id=user.id,
        job_role_id=request.job_role_id,
        job_label=job_label[:200],
        language=language,
        rubric=_rubric_document(),
    )
    db.add(session)
    db.flush()

    for position, question in enumerate(questions[:count], start=1):
        db.add(
            InterviewExchange(
                session_id=session.id,
                position=position,
                question=question.model_dump(),
                answer="",
                feedback={},
            )
        )
    db.commit()
    db.refresh(session)
    return _to_read(session)


def _to_question(document: dict[str, Any]) -> InterviewQuestionRead:
    return InterviewQuestionRead(
        question=str(document.get("question", "")),
        category=document.get("category", "technical"),
        focus=str(document.get("focus", "")),
        difficulty=document.get("difficulty", "intermediate"),
        skill_slugs=list(document.get("skill_slugs") or []),
    )


def _to_feedback(document: dict[str, Any]) -> InterviewFeedbackRead | None:
    """Turn a stored feedback document into the API shape.

    The total is computed here from the per-dimension ratings, never read from
    the stored document. A model cannot hand the application a score.
    """
    if not document:
        return None
    ratings = document.get("ratings") or {}
    notes = list(document.get("dimension_notes") or [])

    dimensions: list[RubricDimensionRead] = []
    total = 0
    for index, item in enumerate(RUBRIC_DIMENSIONS):
        raw = ratings.get(item["key"], 0)
        try:
            score = max(0, min(RUBRIC_MAX_PER_DIMENSION, int(raw)))
        except (TypeError, ValueError):
            score = 0
        total += score
        note = notes[index] if index < len(notes) else ""
        dimensions.append(
            RubricDimensionRead(
                key=item["key"],
                label=item["label"],
                description=item["description"],
                score=score,
                max_score=RUBRIC_MAX_PER_DIMENSION,
                note=note,
            )
        )

    return InterviewFeedbackRead(
        strengths=list(document.get("strengths") or []),
        missed_points=list(document.get("missed_points") or []),
        technical_inaccuracies=list(document.get("technical_inaccuracies") or []),
        clarity_improvements=list(document.get("clarity_improvements") or []),
        example_answer=str(document.get("example_answer", "")),
        further_practice=list(document.get("further_practice") or []),
        dimensions=dimensions,
        practice_score=total,
        max_practice_score=RUBRIC_MAX_TOTAL,
    )


def _to_read(session: InterviewSession) -> InterviewSessionRead:
    exchanges: list[InterviewExchangeRead] = []
    for exchange in session.exchanges:
        exchanges.append(
            InterviewExchangeRead(
                position=exchange.position,
                question=_to_question(exchange.question or {}),
                answer=exchange.answer or "",
                feedback=_to_feedback(exchange.feedback or {}),
            )
        )
    return InterviewSessionRead(
        id=session.id,
        job_role_id=session.job_role_id,
        job_label=session.job_label,
        language=session.language,
        created_at=session.created_at.isoformat(),
        rubric=_rubric_dimensions(),
        exchanges=exchanges,
    )


def answer(
    db: Session,
    user: User,
    session_id: int,
    request: InterviewAnswerRequest,
) -> InterviewExchangeRead:
    """Assess one answer and store the feedback."""
    groq_service.require_provider()
    session = _load_session(db, user, session_id)
    text = request.answer.strip()
    if len(text) < MIN_ANSWER_CHARS:
        raise UnprocessableError(
            "That answer is too short to assess. Write a few sentences about "
            "how you would approach the question.",
            code="answer_too_short",
        )

    exchange = _pick_exchange(session, request.position)
    question = str((exchange.question or {}).get("question", ""))

    facts = ai_context_service.build_facts(db, user, job_role_id=session.job_role_id)
    messages = prompts.interview_feedback_prompt(
        question=question,
        answer=text,
        rubric=list(RUBRIC_DIMENSIONS),
        facts=facts,
        language=session.language,
    )
    feedback = groq_service.run_structured(
        messages,
        InterviewFeedbackOutput,
        schema_name="interview_feedback",
        reasoning_effort="medium",
        max_completion_tokens=4000,
    )

    document = feedback.model_dump()
    # The per-dimension ratings are clamped to the rubric's range before they
    # are stored, so a session's numbers are always inside the rubric it was
    # created with.
    ratings = document.get("ratings") or {}
    document["ratings"] = {
        item["key"]: max(0, min(RUBRIC_MAX_PER_DIMENSION, int(ratings.get(item["key"], 0) or 0)))
        for item in RUBRIC_DIMENSIONS
    }

    exchange.answer = text
    exchange.feedback = document
    db.commit()
    db.refresh(exchange)
    return InterviewExchangeRead(
        position=exchange.position,
        question=_to_question(exchange.question or {}),
        answer=exchange.answer,
        feedback=_to_feedback(exchange.feedback or {}),
    )


def _pick_exchange(session: InterviewSession, position: int | None) -> InterviewExchange:
    if position is not None:
        for exchange in session.exchanges:
            if exchange.position == position:
                return exchange
        raise NotFoundError("That question is not part of this interview session.")
    for exchange in session.exchanges:
        if not exchange.answer:
            return exchange
    raise NotFoundError("Every question in this session has already been answered.")


def next_question(db: Session, user: User, session_id: int) -> InterviewQuestionRead:
    """A follow-up question, based on the previous answer."""
    groq_service.require_provider()
    session = _load_session(db, user, session_id)
    answered = [item for item in session.exchanges if item.answer]
    if not answered:
        raise NotFoundError("Answer a question first — a follow-up is based on your answer.")
    previous = answered[-1]
    question = str((previous.question or {}).get("question", ""))

    facts = ai_context_service.build_facts(db, user, job_role_id=session.job_role_id)
    messages = prompts.interview_follow_up_prompt(
        role_title=session.job_label,
        question=question,
        answer=previous.answer,
        facts=facts,
        language=session.language,
    )
    follow_up = groq_service.run_structured(
        messages,
        InterviewQuestionOutput,
        schema_name="interview_follow_up",
        reasoning_effort="low",
        max_completion_tokens=1500,
    )
    return _to_question(follow_up.model_dump())


def list_sessions(
    db: Session, user: User, *, limit: int, offset: int
) -> tuple[int, list[InterviewSessionSummaryRead]]:
    """The user's interview history, newest first."""
    total = int(
        db.scalar(
            select(func.count())
            .select_from(InterviewSession)
            .where(InterviewSession.user_id == user.id)
        )
        or 0
    )
    sessions = list(
        db.scalars(
            select(InterviewSession)
            .options(selectinload(InterviewSession.exchanges))
            .where(InterviewSession.user_id == user.id)
            .order_by(InterviewSession.created_at.desc(), InterviewSession.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    summaries: list[InterviewSessionSummaryRead] = []
    for session in sessions:
        scores = [
            feedback.practice_score
            for feedback in (_to_feedback(exchange.feedback or {}) for exchange in session.exchanges)
            if feedback is not None
        ]
        summaries.append(
            InterviewSessionSummaryRead(
                id=session.id,
                job_role_id=session.job_role_id,
                job_label=session.job_label,
                language=session.language,
                created_at=session.created_at.isoformat(),
                answered_count=sum(1 for item in session.exchanges if item.answer),
                question_count=len(session.exchanges),
                average_practice_score=(
                    round(sum(scores) / len(scores)) if scores else None
                ),
            )
        )
    return total, summaries


def get_session(db: Session, user: User, session_id: int) -> InterviewSessionRead:
    """One session with its exchanges and feedback."""
    return _to_read(_load_session(db, user, session_id))


def delete_session(db: Session, user: User, session_id: int) -> None:
    """Remove a session and its exchanges."""
    session = _load_session(db, user, session_id)
    db.delete(session)
    db.commit()
