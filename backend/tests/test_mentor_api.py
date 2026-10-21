"""The AI career mentor.

The mentor is only worth having if its answers are about *this* user. These
tests are mostly about that: the prompt must carry the user's own record, the
answer must be reported as grounded in it, and the assistant must say when the
record does not contain what was asked for.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

ASK = "/api/ai/mentor/ask"


def _answer(text: str) -> str:
    return text


def test_the_mentor_requires_authentication(client: TestClient, groq) -> None:
    response = client.post(ASK, json={"message": "Which role fits me?"})
    assert response.status_code == 401


def test_the_mentor_answers_a_question(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply(_answer("Start with the roles your confirmed skills already support."))
    response = client.post(ASK, json={"message": "Which role fits me?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("Start with the roles")
    assert body["language"] == "en"
    assert body["generated_by"].startswith("groq:")


def test_the_prompt_carries_the_users_own_record(
    client: TestClient, auth_client, groq, db, taxonomy_seed
) -> None:
    """Without the user's own facts, the answer is a generic essay."""
    from app.models.profile import Profile
    from app.models.user_skill import UserSkill

    auth, user = auth_client()
    profile = db.query(Profile).filter(Profile.user_id == user.id).one()
    profile.headline = "Data Analyst"
    profile.career_goal = "Work with data"
    db.commit()

    from app.models.skill import Skill

    skill = db.query(Skill).filter(Skill.slug == "python").one()
    db.add(UserSkill(user_id=user.id, skill_id=skill.id, proficiency=4, confirmed=True))
    db.commit()

    groq.reply(_answer("Your Python is your strongest asset."))
    response = client.post(ASK, json={"message": "What should I do next?"})
    assert response.status_code == 200

    prompt = groq.calls[0]["messages"][0]["content"]
    assert "Data Analyst" in prompt
    assert "Python" in prompt
    assert "Work with data" in prompt


def test_the_answer_reports_which_records_it_used(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply(_answer("A short answer."))
    response = client.post(ASK, json={"message": "What should I do next?"})
    body = response.json()
    assert isinstance(body["context_used"], list)
    assert body["context_used"] == [] or isinstance(body["context_used"][0], str)


def test_the_assistant_admits_when_the_record_is_thin(
    client: TestClient, auth_client, groq
) -> None:
    """A user with nothing recorded must be told that, not given a confident
    answer about their career."""
    auth, _user = auth_client()
    groq.reply(_answer("Once you add your skills I can be specific."))
    response = client.post(ASK, json={"message": "Which role fits me?"})
    body = response.json()
    joined = " ".join(body["limitations"])
    assert "no confirmed skills" in joined
    assert "projects" in joined


def test_the_assistant_says_when_there_is_no_ranking_to_explain(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply(_answer("Run the engine first."))
    response = client.post(
        ASK, json={"message": "Why did the engine rank Data Analyst first?"}
    )
    joined = " ".join(response.json()["limitations"])
    assert "recommendation run" in joined


def test_the_assistant_will_not_invent_a_salary(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply(_answer("This application holds no salary data."))
    response = client.post(ASK, json={"message": "What is the salary for a data analyst?"})
    joined = " ".join(response.json()["limitations"])
    assert "salary" in joined.lower()


def test_the_conversation_window_is_bounded(
    client: TestClient, auth_client, groq
) -> None:
    """Only the last few turns are sent, so a long chat cannot grow the
    request without bound."""
    auth, _user = auth_client()
    groq.reply(_answer("Following up."))
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"turn {index}"}
        for index in range(40)
    ]
    response = client.post(
        ASK, json={"message": "And the second one?", "history": history}
    )
    assert response.status_code == 200
    prompt = groq.calls[0]["messages"][0]["content"]
    assert "turn 39" in prompt
    assert "turn 0 " not in prompt


def test_a_request_over_the_size_limit_is_refused(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.post(ASK, json={"message": "x" * 5_000})
    assert response.status_code == 422


def test_an_empty_question_is_refused(client: TestClient, auth_client, groq) -> None:
    auth, _user = auth_client()
    response = client.post(ASK, json={"message": ""})
    assert response.status_code == 422


def test_the_mentor_focuses_on_a_role_when_one_is_named(
    client: TestClient, auth_client, groq, role_seed
) -> None:
    auth, _user = auth_client()
    role = role_seed[0]
    groq.reply(_answer("For that role, the gap is Docker."))
    response = client.post(
        ASK, json={"message": "What should I learn?", "job_role_id": role.id}
    )
    assert response.status_code == 200
    prompt = groq.calls[0]["messages"][0]["content"]
    assert role.title in prompt
    assert "coverage" in prompt


def test_a_provider_failure_is_a_502_and_not_a_leak(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    from app.ml.groq import GroqServerError

    groq.fail(GroqServerError("provider failed (503)"))
    response = client.post(ASK, json={"message": "hello"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_unavailable"
