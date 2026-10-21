"""The mock interview simulator.

The simulator's value depends on the feedback being honest, and the practice
score being a *practice* score. These tests pin down the parts that could
quietly go wrong: a score the model dictated rather than the application
computing, a score presented as a hiring prediction, and a session another
user could read.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview import InterviewExchange, InterviewSession

INTERVIEWS = "/api/ai/interviews"


def _questions(count: int = 3) -> dict:
    return {
        "questions": [
            {
                "question": f"Question {index}: how would you approach it?",
                "category": "technical" if index % 2 == 0 else "project",
                "focus": "Whether the candidate reasons about the problem.",
                "difficulty": "intermediate",
                "skill_slugs": ["python"],
            }
            for index in range(1, count + 1)
        ]
    }


def _feedback(relevance: int = 4, correctness: int = 3) -> dict:
    return {
        "strengths": ["You named the trade-off before choosing an approach."],
        "missed_points": ["You did not say what you would measure afterwards."],
        "technical_inaccuracies": [],
        "clarity_improvements": ["Lead with the conclusion."],
        "example_answer": "I would start by ... and measure ...",
        "further_practice": ["Practise writing the follow-up metric."],
        "ratings": {
            "relevance": relevance,
            "correctness": correctness,
            "completeness": 3,
            "reasoning": 4,
            "clarity": 2,
        },
        "dimension_notes": [
            "Answered the question directly.",
            "One statement was imprecise.",
            "Missed the measurement step.",
            "The reasoning was visible.",
            "The structure could be tighter.",
        ],
    }


def test_an_interview_is_started_and_its_questions_saved(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(3))

    response = client.post(INTERVIEWS, json={"job_role_id": role.id, "question_count": 3})
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["exchanges"]) == 3
    assert body["job_label"] == role.title
    assert body["language"] == "en"


def test_the_questions_come_from_the_role_and_the_candidate(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(2))
    client.post(INTERVIEWS, json={"job_role_id": role.id, "question_count": 2})
    prompt = groq.calls[0]["messages"][0]["content"]
    assert role.title in prompt
    assert "SQL" in prompt


def test_an_answer_is_assessed_and_the_feedback_is_saved(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(2))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 2}
    ).json()

    groq.reply_json(_feedback())
    response = client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "I would build a small pipeline and measure the runtime."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["feedback"]["strengths"]
    assert body["feedback"]["missed_points"]
    assert body["feedback"]["example_answer"]
    assert body["feedback"]["practice_score"] == 16
    assert body["feedback"]["max_practice_score"] == 25


def test_the_practice_score_is_computed_by_the_application(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    """The model reports a rating per dimension; the application does the sum.

    A model that could dictate a total could hand somebody a number that
    disagrees with the dimensions printed next to it.
    """
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()

    groq.reply_json(_feedback(relevance=5, correctness=5))
    body = client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "A long enough answer to be assessed properly."},
    ).json()
    feedback = body["feedback"]
    assert feedback["practice_score"] == sum(
        dimension["score"] for dimension in feedback["dimensions"]
    )
    assert feedback["practice_score"] == 19


def test_a_rating_outside_the_rubric_range_is_clamped(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()

    document = _feedback()
    document["ratings"]["relevance"] = 9
    groq.reply_json(document)
    body = client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "A long enough answer to be assessed properly."},
    ).json()
    relevance = next(
        dimension for dimension in body["feedback"]["dimensions"]
        if dimension["key"] == "relevance"
    )
    assert relevance["score"] == 5


def test_the_score_is_labelled_as_a_practice_score(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    """The number must never read as a prediction of hiring."""
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()
    groq.reply_json(_feedback())
    body = client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "A long enough answer to be assessed properly."},
    ).json()
    note = body["feedback"]["score_note"].lower()
    assert "practice score" in note
    assert "not a prediction of hiring success" in note


def test_the_rubric_is_stored_with_the_session(
    client: TestClient, auth_client, groq, role_seed, db: Session
) -> None:
    """A score has to stay explicable months later."""
    auth, user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()

    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == created["id"], InterviewSession.user_id == user.id
        )
    )
    assert session is not None
    keys = {item["key"] for item in session.rubric}
    assert keys == {"relevance", "correctness", "completeness", "reasoning", "clarity"}


def test_the_feedback_is_readable_again_later(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()
    groq.reply_json(_feedback())
    client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "A long enough answer to be assessed properly."},
    )

    reread = client.get(f"{INTERVIEWS}/{created['id']}").json()
    assert reread["exchanges"][0]["answer"]
    assert reread["exchanges"][0]["feedback"]["practice_score"] == 16


def test_a_user_cannot_read_another_users_session(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _owner = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()

    other, _other = auth_client()
    assert other.get(f"{INTERVIEWS}/{created['id']}").status_code == 404
    assert other.delete(f"{INTERVIEWS}/{created['id']}").status_code == 404
    assert (
        other.post(
            f"{INTERVIEWS}/{created['id']}/answers",
            json={"answer": "A long enough answer to be assessed properly."},
        ).status_code
        == 404
    )


def test_the_session_list_shows_only_the_users_own_sessions(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    client.post(INTERVIEWS, json={"job_role_id": role.id, "question_count": 1})

    other, _other = auth_client()
    body = other.get(INTERVIEWS).json()
    assert body["total"] == 0


def test_a_follow_up_question_is_asked_from_the_previous_answer(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()
    groq.reply_json(_feedback())
    client.post(
        f"{INTERVIEWS}/{created['id']}/answers",
        json={"answer": "A long enough answer to be assessed properly."},
    )

    groq.reply_json(
        {
            "question": "You mentioned a nightly report. What happens if it fails?",
            "category": "follow_up",
            "focus": "Operational thinking.",
            "difficulty": "intermediate",
            "skill_slugs": [],
        }
    )
    response = client.post(f"{INTERVIEWS}/{created['id']}/next-question")
    assert response.status_code == 200
    assert response.json()["category"] == "follow_up"


def test_an_answer_that_is_too_short_is_refused(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(1))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 1}
    ).json()
    response = client.post(f"{INTERVIEWS}/{created['id']}/answers", json={"answer": "yes"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "answer_too_short"


def test_an_interview_with_no_role_and_no_description_is_refused(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.post(INTERVIEWS, json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_job_description"


def test_a_session_can_be_deleted(
    client: TestClient, auth_client, groq, role_seed, db: Session
) -> None:
    auth, user = auth_client()
    role = role_seed[2]
    groq.reply_json(_questions(2))
    created = client.post(
        INTERVIEWS, json={"job_role_id": role.id, "question_count": 2}
    ).json()
    assert client.delete(f"{INTERVIEWS}/{created['id']}").status_code == 204
    assert client.get(f"{INTERVIEWS}/{created['id']}").status_code == 404
    remaining = db.scalars(
        select(InterviewExchange).where(InterviewExchange.session_id == created["id"])
    ).all()
    assert remaining == []
