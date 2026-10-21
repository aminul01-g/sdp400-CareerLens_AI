"""The learning roadmap.

Three things have to be true for a roadmap to be worth following, and each
has a test here:

* it is built from the engine's own gap report, so it targets the skills the
  application actually says are missing;
* it cannot contain a skill the engine did not report, or a link the
  registry does not hold — a plan that sends somebody to an invented URL is
  worse than no plan;
* it is saved, and the learner's progress on it is saved beside it, scoped to
  its owner.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.roadmap import LearningRoadmap, LearningRoadmapTask
from app.models.skill import Skill
from app.models.user import User
from app.models.user_skill import UserSkill

ROADMAPS = "/api/ai/roadmaps"


def _plan_document(*, skill_name: str = "", resource_ids: list[str] | None = None) -> dict:
    return {
        "target_role": "Data Analyst",
        "starting_profile": "A student with Python and some SQL.",
        "strengths": ["Python", "SQL"],
        "skill_gaps": ["Pandas"],
        "learning_objectives": ["Learn Pandas first."],
        "tasks": [
            {
                "week": 1,
                "title": "Read the pandas user guide",
                "objective": "Be able to load and filter a tabular file.",
                "activities": ["Work through the introduction."],
                "deliverable": "A notebook that loads a CSV.",
                "completion_criteria": ["The notebook runs and prints a filtered frame."],
                "estimated_hours": 4.0,
                "skill_name": skill_name,
                "resource_ids": resource_ids if resource_ids is not None else ["pandas-docs"],
                "portfolio_hint": "This becomes the data-loading module of the project.",
            },
            {
                "week": 2,
                "title": "Build a small dashboard",
                "objective": "Present one finding clearly.",
                "activities": ["Chart two things."],
                "deliverable": "A chart with a caption.",
                "completion_criteria": ["The chart has a title and a one-line conclusion."],
                "estimated_hours": 5.0,
                "skill_name": "",
                "resource_ids": [],
                "portfolio_hint": "",
            },
        ],
        "portfolio_project": {
            "title": "Public spending explorer",
            "problem_statement": "Nobody can see where a city budget goes.",
            "required_technologies": ["Python", "Pandas"],
            "milestones": ["Load the data", "Clean it", "Publish the charts"],
            "expected_outputs": ["A repository", "A written README"],
            "evaluation_criteria": ["It runs from a clean checkout."],
            "demonstrates_skills": ["Pandas"],
        },
        "portfolio_presentation": ["Write a README that states the finding first."],
        "total_estimated_hours": 9.0,
        "notes": "",
    }


def _seed_user_skill(db: Session, user: User, slug: str) -> None:
    skill = db.scalar(select(Skill).where(Skill.slug == slug))
    assert skill is not None
    db.add(
        UserSkill(
            user_id=user.id,
            skill_id=skill.id,
            proficiency=4,
            confirmed=True,
            years_used=Decimal("1.0"),
        )
    )
    db.commit()


def test_a_roadmap_is_generated_and_saved(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, db
) -> None:
    auth, user = auth_client()
    role = role_seed[2]  # Data Analyst
    groq.reply_json(_plan_document())

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["duration_weeks"] == 4
    assert body["title"].startswith(role.title)
    assert len(body["tasks"]) == 2
    assert body["total_tasks"] == 2
    assert body["completed_tasks"] == 0
    assert body["progress_pct"] == 0.0

    stored = db.scalar(select(LearningRoadmap).where(LearningRoadmap.user_id == user.id))
    assert stored is not None
    assert stored.duration_weeks == 4
    assert len(stored.tasks) == 2


def test_the_plan_targets_the_gaps_the_engine_reported(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, db
) -> None:
    """The gap report decides which skills the plan is about."""
    auth, user = auth_client()
    role = role_seed[2]
    _seed_user_skill(db, user, "python")
    _seed_user_skill(db, user, "sql")

    groq.reply_json(_plan_document())
    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    prompt = groq.calls[0]["messages"][0]["content"]
    gap_block = prompt.split("<verified_skill_gaps>")[1].split("</verified_skill_gaps>")[0]
    assert "Pandas" in gap_block
    assert "PostgreSQL" in gap_block
    # SQL is a requirement the user already meets, so it is not a gap.
    assert "- SQL (importance" not in gap_block


def test_a_skill_the_engine_did_not_report_is_discarded(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """The model cannot add a skill the gap report did not produce.

    "Kubernetes" is a real skill in the taxonomy, and it is not one of this
    role's gaps, so it is discarded: being a real skill is not the same as
    being a gap.
    """
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document(skill_name="Kubernetes"))

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    assert response.json()["tasks"][0]["skill_slug"] == ""


def test_a_learning_resource_the_registry_does_not_hold_is_discarded(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """The model is shown identifiers, never URLs, so an invented link has
    nowhere to live."""
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document(resource_ids=["pandas-docs", "totally-made-up"]))

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    resources = response.json()["tasks"][0]["resources"]
    assert [item["id"] for item in resources] == ["pandas-docs"]
    assert resources[0]["url"].startswith("https://")


def test_the_url_comes_from_the_registry_and_not_from_the_model(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document())
    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    resources = response.json()["tasks"][0]["resources"]
    assert resources[0]["url"] == "https://pandas.pydata.org/docs/"
    prompt = groq.calls[0]["messages"][0]["content"]
    assert "https://" not in prompt.split("<verified_learning_resources>")[1]


def test_a_task_beyond_the_requested_length_is_dropped(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    document = _plan_document()
    document["tasks"][0]["week"] = 9
    groq.reply_json(document)

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    weeks = [task["week"] for task in response.json()["tasks"]]
    assert all(1 <= week <= 4 for week in weeks)


def test_progress_is_recorded_and_kept_beside_the_plan(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, db
) -> None:
    auth, user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document())
    created = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    ).json()

    key = created["tasks"][0]["task_key"]
    response = client.patch(
        f"{ROADMAPS}/{created['id']}/tasks/{key}",
        json={
            "is_complete": True,
            "notes": "Finished the first chapter.",
            "portfolio_url": "https://github.com/example/notebook",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is True
    assert body["notes"] == "Finished the first chapter."
    assert body["portfolio_url"] == "https://github.com/example/notebook"
    assert body["completed_at"] is not None

    reread = client.get(f"{ROADMAPS}/{created['id']}").json()
    assert reread["completed_tasks"] == 1
    assert reread["progress_pct"] == 50.0


def test_a_user_cannot_read_another_users_plan(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, make_user
) -> None:
    """404, not 403: a 403 would confirm that the id exists."""
    auth, _owner = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document())
    created = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    ).json()

    other_client, _other = auth_client()
    assert other_client.get(f"{ROADMAPS}/{created['id']}").status_code == 404
    assert other_client.delete(f"{ROADMAPS}/{created['id']}").status_code == 404
    assert (
        other_client.patch(
            f"{ROADMAPS}/{created['id']}/tasks/{created['tasks'][0]['task_key']}",
            json={"is_complete": True},
        ).status_code
        == 404
    )


def test_the_list_only_shows_the_users_own_plans(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, make_user
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document())
    client.post(ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4})

    other_client, _other = auth_client()
    body = other_client.get(ROADMAPS).json()
    assert body["total"] == 0
    assert body["items"] == []


def test_a_plan_for_a_role_that_does_not_exist_is_a_404(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.post(ROADMAPS, json={"job_role_id": 999_999, "duration_weeks": 4})
    assert response.status_code == 404


def test_only_four_and_six_week_plans_are_accepted(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 5}
    )
    assert response.status_code == 422


def test_a_saved_plan_can_be_deleted(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, db
) -> None:
    auth, user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document())
    created = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    ).json()

    assert client.delete(f"{ROADMAPS}/{created['id']}").status_code == 204
    assert client.get(f"{ROADMAPS}/{created['id']}").status_code == 404
    remaining = db.scalars(
        select(LearningRoadmapTask).where(
            LearningRoadmapTask.roadmap_id == created["id"]
        )
    ).all()
    assert remaining == []


def test_a_plausible_but_wrong_provider_document_is_refused(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """A response that does not match the schema is refused, not coerced."""
    auth, _user = auth_client()
    role = role_seed[2]
    # Missing everything else. Queued twice: once, and once more after the
    # bounded retry adds the output-shape rule to the prompt.
    groq.reply_json({"target_role": "Data Analyst"})
    groq.reply_json({"target_role": "Data Analyst"})

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_a_skill_the_model_writes_by_name_is_resolved(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """A name and a slug are the same skill to a person and not the same
    string to a program.

    The provider writes the skill's *name* -- "Pandas" -- because that is
    what the prompt shows it and what a person would write. The application
    stores slugs, because that is what the taxonomy uses. Without a
    resolution step between the two, every skill link and every learning
    resource in the plan is silently dropped.
    """
    auth, _user = auth_client()
    role = role_seed[2]  # Data Analyst: sql, python, pandas, postgresql
    # A user with no confirmed skills has every requirement as a gap, so
    # "Pandas" really is one.
    groq.reply_json(_plan_document(skill_name="Pandas", resource_ids=["pandas-docs"]))

    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201, response.text
    task = response.json()["tasks"][0]
    assert task["skill_slug"] == "pandas"
    assert [item["id"] for item in task["resources"]] == ["pandas-docs"]
    assert task["resources"][0]["url"] == "https://pandas.pydata.org/docs/"


def test_the_projects_skill_list_is_resolved_the_same_way(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """The same rule applies to the portfolio project's skill list."""
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document(skill_name="Pandas"))
    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    project = response.json()["portfolio_project"]
    assert project["demonstrates_skills"] == ["pandas"]


def test_a_skill_that_is_not_a_gap_is_still_refused(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """Resolving a name is not the same as accepting it.

    "Kubernetes" is in the taxonomy, so it resolves -- and it is not one of
    this role's gaps, so it is discarded. A plan built around a skill the
    engine did not report as missing would send the learner down the wrong
    path.
    """
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_plan_document(skill_name="Kubernetes"))
    response = client.post(
        ROADMAPS, json={"job_role_id": role.id, "duration_weeks": 4}
    )
    assert response.status_code == 201
    assert response.json()["tasks"][0]["skill_slug"] == ""
