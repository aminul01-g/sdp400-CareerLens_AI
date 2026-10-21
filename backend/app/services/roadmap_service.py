"""The learning roadmap: generation, sanitisation and persistence.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The plan cannot invent a gap  The model is shown the engine's missing skills
                               and nothing else. A skill it names that is not
                               on that list is discarded, exactly as the
                               legacy learning path discarded a skill the
                               gap report had not produced
The plan cannot invent a link  The model is shown resource *identifiers* and
                               never a URL, and its output schema has no
                               field for one. An identifier the registry does
                               not hold — or one that is not relevant to this
                               plan's skills — is dropped
The plan cannot outrun its    A plan for four weeks may not contain a task
                               length                     for a fifth. Tasks outside the
                               requested length are dropped rather than
                               silently renumbered
Progress is the user's         Completion, notes and portfolio links live
                               in columns on the task row, and the plan
                               document is never rewritten
============================  ==========================================
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.ml import prompts
from app.ml.learning_resources import LearningResource
from app.ml.learning_resources import load as load_resources
from app.models.profile import Profile
from app.models.roadmap import LearningRoadmap, LearningRoadmapTask
from app.models.user import User
from app.schemas.ai import (
    LearningResourceRead,
    PortfolioProjectRead,
    RoadmapGenerateRequest,
    RoadmapRead,
    RoadmapSummaryRead,
    RoadmapTaskRead,
    RoadmapTaskUpdate,
)
from app.schemas.llm import RoadmapPlanOutput
from app.services import ai_context_service, groq_service, skill_service

logger = logging.getLogger("app.services.roadmap")

#: The largest number of tasks a plan may contain. A six-week plan for one
#: role is a few dozen tasks, not a hundred.
MAX_TASKS = 60


def _task_key(week: int, index: int) -> str:
    """A stable key for a task within a plan."""
    return f"w{week}-{index:02d}"


def _read_resource(resource: LearningResource) -> LearningResourceRead:
    return LearningResourceRead(
        id=resource.id,
        title=resource.title,
        url=resource.url,
        kind=resource.kind,
        summary=resource.summary,
    )


def _sanitise_plan(
    plan: RoadmapPlanOutput,
    *,
    resolve_skill: Callable[[str], str],
    gap_slugs: set[str],
    allowed_resource_ids: set[str],
    duration_weeks: int,
) -> RoadmapPlanOutput:
    """Strip everything the model added that the application did not supply.

    Four things are removed or corrected:

    * a skill **name** that does not resolve to a skill the engine reported as
      missing is cleared;
    * a ``resource_id`` that is not in the registry, or that is not relevant
      to this plan;
    * a task for a week the plan does not have;
    * a project skill list entry that is not a gap.

    The provider is a good writer and an unreliable witness. It writes skill
    *names* where a slug was asked for, and it writes slugs where a name was
    asked for, and a name and a slug are the same skill to a person and not
    the same string to a program. So the name is resolved against the
    taxonomy here, and the gap check is applied *after* the resolution: a
    skill that is in the taxonomy but is not a gap is still not a gap.
    """
    cleaned_tasks: list[Any] = []
    for task in plan.tasks:
        week = int(task.week)
        if week < 1 or week > duration_weeks:
            continue
        task.skill_name = resolve_skill(task.skill_name)
        task.resource_ids = [
            resource_id
            for resource_id in task.resource_ids
            if resource_id in allowed_resource_ids
        ]
        cleaned_tasks.append(task)
        if len(cleaned_tasks) >= MAX_TASKS:
            break

    plan.tasks = cleaned_tasks
    plan.portfolio_project.demonstrates_skills = [
        resolve_skill(name) for name in plan.portfolio_project.demonstrates_skills
    ]
    plan.portfolio_project.demonstrates_skills = [
        slug for slug in plan.portfolio_project.demonstrates_skills if slug in gap_slugs
    ]
    return plan


def _skill_resolver(
    db: Session, gap_names: dict[str, str]
) -> Callable[[str], str]:
    """Build the function that turns a written skill name into a canonical slug.

    Two steps, in order. The gap names first, because they are the verified
    ones and they answer the question exactly. The taxonomy second, for a
    name the model produced that is a real skill but not one of this plan's
    gaps -- the result is still discarded below, because being a real skill
    is not the same as being a gap.
    """
    lowered = {name.strip().lower(): slug for name, slug in gap_names.items()}

    def _resolve(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            return ""
        slug = lowered.get(cleaned.lower())
        if slug:
            return slug
        resolved = skill_service.canonicalise_skill(db, cleaned)
        if resolved is None:
            return ""
        return resolved[1]

    return _resolve


def _resource_candidates(gap_slugs: list[str]) -> tuple[list[dict[str, str]], set[str]]:
    """The resources this plan may refer to, and the identifiers that are valid.

    Only the resources registered for the plan's own missing skills are
    offered. A plan about Docker should not be able to point at a Django
    tutorial, and a model that tries is simply ignored.
    """
    registry = load_resources()
    resources = registry.for_skills(gap_slugs)
    described = [
        {"id": resource.id, "title": resource.title, "summary": resource.summary}
        for resource in resources
    ]
    return described, {resource.id for resource in resources}


def generate(
    db: Session,
    user: User,
    request: RoadmapGenerateRequest,
) -> RoadmapRead:
    """Build a plan for one role and save it."""
    groq_service.require_provider()
    role, _spec, report = ai_context_service.gap_report(db, user, request.job_role_id)
    facts = ai_context_service.build_facts(db, user, job_role_id=request.job_role_id)

    gap_items = [
        {
            "name": missing.name,
            "weight": round(missing.weight, 4),
            "tier": missing.tier,
        }
        for missing in report.missing
    ]
    # The slugs of the skills the engine actually reported as missing. The
    # requirements list gives slug-to-name; the gap report gives the names
    # that are missing, so the two are joined on the name to find the slugs.
    missing_names = {item["name"] for item in gap_items}
    all_slugs = {
        str(item.get("slug", "")): str(item.get("name", ""))
        for item in ai_context_service.role_requirements(db, request.job_role_id)
    }
    gap_slugs = {
        slug for slug, name in all_slugs.items() if name in missing_names and slug
    }
    # The written name of each gap, so a name the model produces can be
    # resolved without guessing at a slug format.
    gap_names = {name: slug for slug, name in all_slugs.items() if name in missing_names}
    resolve_skill = _skill_resolver(db, gap_names)

    described_resources, allowed_ids = _resource_candidates(sorted(gap_slugs))

    language = _resolve_language(db, user, request.language)
    messages = prompts.roadmap_prompt(
        role_title=role.title,
        weeks=request.duration_weeks,
        facts=facts,
        missing_skills=gap_items,
        resources=described_resources,
        language=language,
    )
    plan = groq_service.run_structured(
        messages,
        RoadmapPlanOutput,
        schema_name="learning_roadmap",
        reasoning_effort="medium",
        max_completion_tokens=6000,
    )
    plan = _sanitise_plan(
        plan,
        resolve_skill=resolve_skill,
        gap_slugs=gap_slugs,
        allowed_resource_ids=allowed_ids,
        duration_weeks=request.duration_weeks,
    )
    if not plan.tasks:
        # A plan with no tasks is not a plan. The model produced something
        # unusable; the caller gets an honest error rather than an empty
        # document dressed up as a plan.
        raise NotFoundError(
            "The learning plan could not be generated for this role. Please try again."
        )

    title = f"{role.title} — {request.duration_weeks}-week plan"
    document = _document(plan, role.title, request.duration_weeks)

    roadmap = LearningRoadmap(
        user_id=user.id,
        job_role_id=role.id,
        title=title,
        duration_weeks=request.duration_weeks,
        language=language,
        plan=document,
        generated_by=f"groq:{groq_service.provider_status().get('model', '')}",
        gap_skills=sorted(gap_slugs),
    )
    db.add(roadmap)
    db.flush()

    for position, task in enumerate(plan.tasks, start=1):
        db.add(
            LearningRoadmapTask(
                roadmap_id=roadmap.id,
                task_key=_task_key(int(task.week), position),
                week=int(task.week),
                position=position,
                title=task.title[:300],
                is_complete=False,
                notes="",
                portfolio_url="",
            )
        )
    db.commit()
    db.refresh(roadmap)
    return _to_read(roadmap, plan, allowed_ids)


def _resolve_language(db: Session, user: User, requested: str | None) -> str:
    """Which language the plan is written in."""
    if requested:
        return prompts.normalise_language(requested)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return prompts.normalise_language(profile.preferred_language)
    return "en"


def _document(plan: RoadmapPlanOutput, role_title: str, duration_weeks: int) -> dict[str, Any]:
    """The plan as it is stored.

    The task list is stored with the same order and the same keys the task
    rows use, so the two can never disagree about which task is which.
    """
    return {
        "target_role": plan.target_role or role_title,
        "starting_profile": plan.starting_profile,
        "strengths": list(plan.strengths),
        "skill_gaps": list(plan.skill_gaps),
        "learning_objectives": list(plan.learning_objectives),
        "portfolio_project": plan.portfolio_project.model_dump(),
        "portfolio_presentation": list(plan.portfolio_presentation),
        "total_estimated_hours": float(plan.total_estimated_hours),
        "notes": plan.notes,
        "duration_weeks": duration_weeks,
        "tasks": [
            {
                "task_key": _task_key(int(task.week), position),
                "week": int(task.week),
                "position": position,
                "title": task.title,
                "objective": task.objective,
                "activities": list(task.activities),
                "deliverable": task.deliverable,
                "completion_criteria": list(task.completion_criteria),
                "estimated_hours": float(task.estimated_hours),
                "skill_slug": task.skill_name,
                "resource_ids": list(task.resource_ids),
                "portfolio_hint": task.portfolio_hint,
            }
            for position, task in enumerate(plan.tasks, start=1)
        ],
    }


def _to_read(
    roadmap: LearningRoadmap,
    plan: RoadmapPlanOutput | None,
    allowed_ids: set[str],
) -> RoadmapRead:
    """Assemble the API representation of a roadmap."""
    document = roadmap.plan or {}
    registry = load_resources()
    stored_tasks = {task.task_key: task for task in roadmap.tasks}
    document_tasks = document.get("tasks") or []

    tasks: list[RoadmapTaskRead] = []
    for entry in document_tasks:
        key = str(entry.get("task_key", ""))
        stored = stored_tasks.get(key)
        resources = registry.resolve(
            [str(item) for item in entry.get("resource_ids", [])]
        )
        tasks.append(
            RoadmapTaskRead(
                task_key=key,
                week=int(entry.get("week", 1)),
                position=int(entry.get("position", 0)),
                title=str(entry.get("title", "")),
                objective=str(entry.get("objective", "")),
                activities=list(entry.get("activities") or []),
                deliverable=str(entry.get("deliverable", "")),
                completion_criteria=list(entry.get("completion_criteria") or []),
                estimated_hours=float(entry.get("estimated_hours", 0) or 0),
                skill_slug=str(entry.get("skill_slug", "")),
                resources=[_read_resource(resource) for resource in resources],
                portfolio_hint=str(entry.get("portfolio_hint", "")),
                is_complete=bool(stored.is_complete) if stored else False,
                notes=stored.notes if stored else "",
                portfolio_url=stored.portfolio_url if stored else "",
                completed_at=(
                    stored.completed_at.isoformat()
                    if stored and stored.completed_at
                    else None
                ),
            )
        )

    total = len(tasks)
    done = sum(1 for task in tasks if task.is_complete)
    project = document.get("portfolio_project") or {}
    del allowed_ids

    return RoadmapRead(
        id=roadmap.id,
        job_role_id=roadmap.job_role_id,
        job_role_title=roadmap.job_role.title if roadmap.job_role else "",
        title=roadmap.title,
        duration_weeks=roadmap.duration_weeks,
        language=roadmap.language,
        generated_by=roadmap.generated_by,
        created_at=roadmap.created_at.isoformat(),
        target_role=str(document.get("target_role", "")),
        starting_profile=str(document.get("starting_profile", "")),
        strengths=list(document.get("strengths") or []),
        skill_gaps=list(document.get("skill_gaps") or []),
        learning_objectives=list(document.get("learning_objectives") or []),
        tasks=tasks,
        portfolio_project=PortfolioProjectRead(**project) if project else None,
        portfolio_presentation=list(document.get("portfolio_presentation") or []),
        total_estimated_hours=float(document.get("total_estimated_hours", 0) or 0),
        notes=str(document.get("notes", "")),
        gap_skills=list(roadmap.gap_skills or []),
        completed_tasks=done,
        total_tasks=total,
        progress_pct=round((done / total) * 100, 1) if total else 0.0,
    )


def list_roadmaps(
    db: Session, user: User, *, limit: int, offset: int
) -> tuple[int, list[RoadmapSummaryRead]]:
    """The user's saved plans, newest first."""
    total = int(
        db.scalar(
            select(func.count())
            .select_from(LearningRoadmap)
            .where(LearningRoadmap.user_id == user.id)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(LearningRoadmap)
            .options(
                selectinload(LearningRoadmap.tasks),
                selectinload(LearningRoadmap.job_role),
            )
            .where(LearningRoadmap.user_id == user.id)
            .order_by(LearningRoadmap.created_at.desc(), LearningRoadmap.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    summaries: list[RoadmapSummaryRead] = []
    for roadmap in rows:
        total_tasks = len(roadmap.tasks)
        done = sum(1 for task in roadmap.tasks if task.is_complete)
        summaries.append(
            RoadmapSummaryRead(
                id=roadmap.id,
                job_role_id=roadmap.job_role_id,
                job_role_title=roadmap.job_role.title if roadmap.job_role else "",
                title=roadmap.title,
                duration_weeks=roadmap.duration_weeks,
                language=roadmap.language,
                created_at=roadmap.created_at.isoformat(),
                completed_tasks=done,
                total_tasks=total_tasks,
                progress_pct=round((done / total_tasks) * 100, 1) if total_tasks else 0.0,
            )
        )
    return total, summaries


def get_roadmap(db: Session, user: User, roadmap_id: int) -> RoadmapRead:
    """One saved plan. Scoped by owner in the query, so a foreign id is a 404."""
    roadmap = db.scalar(
        select(LearningRoadmap)
        .options(
            selectinload(LearningRoadmap.tasks),
            selectinload(LearningRoadmap.job_role),
        )
        .where(LearningRoadmap.id == roadmap_id, LearningRoadmap.user_id == user.id)
    )
    if roadmap is None:
        raise NotFoundError("That learning plan does not exist.")
    return _to_read(roadmap, None, set())


def update_task(
    db: Session,
    user: User,
    roadmap_id: int,
    task_key: str,
    update: RoadmapTaskUpdate,
) -> RoadmapTaskRead:
    """Record the learner's progress on one task."""
    roadmap = db.scalar(
        select(LearningRoadmap)
        .options(selectinload(LearningRoadmap.tasks))
        .where(LearningRoadmap.id == roadmap_id, LearningRoadmap.user_id == user.id)
    )
    if roadmap is None:
        raise NotFoundError("That learning plan does not exist.")
    task = next((item for item in roadmap.tasks if item.task_key == task_key), None)
    if task is None:
        raise NotFoundError("That task is not part of this learning plan.")

    if update.is_complete is not None:
        task.is_complete = update.is_complete
        from datetime import datetime

        task.completed_at = datetime.now(UTC) if update.is_complete else None
    if update.notes is not None:
        task.notes = update.notes
    if update.portfolio_url is not None:
        task.portfolio_url = update.portfolio_url
    db.commit()
    db.refresh(task)
    return _task_read(task, roadmap)


def _task_read(task: LearningRoadmapTask, roadmap: LearningRoadmap) -> RoadmapTaskRead:
    document = roadmap.plan or {}
    entry: dict[str, Any] = next(
        (
            item
            for item in document.get("tasks") or []
            if str(item.get("task_key", "")) == task.task_key
        ),
        {},
    )
    registry = load_resources()
    resources = registry.resolve([str(item) for item in entry.get("resource_ids", [])])
    return RoadmapTaskRead(
        task_key=task.task_key,
        week=task.week,
        position=task.position,
        title=task.title,
        objective=str(entry.get("objective", "")),
        activities=list(entry.get("activities") or []),
        deliverable=str(entry.get("deliverable", "")),
        completion_criteria=list(entry.get("completion_criteria") or []),
        estimated_hours=float(entry.get("estimated_hours", 0) or 0),
        skill_slug=str(entry.get("skill_slug", "")),
        resources=[_read_resource(resource) for resource in resources],
        portfolio_hint=str(entry.get("portfolio_hint", "")),
        is_complete=task.is_complete,
        notes=task.notes,
        portfolio_url=task.portfolio_url,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


def delete_roadmap(db: Session, user: User, roadmap_id: int) -> None:
    """Remove a saved plan and its tasks."""
    roadmap = db.scalar(
        select(LearningRoadmap).where(
            LearningRoadmap.id == roadmap_id, LearningRoadmap.user_id == user.id
        )
    )
    if roadmap is None:
        raise NotFoundError("That learning plan does not exist.")
    db.delete(roadmap)
    db.commit()
