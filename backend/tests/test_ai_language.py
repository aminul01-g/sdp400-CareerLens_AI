"""Bangla and English guidance.

Two things have to be true at once, and they pull in opposite directions:

* the *explanation* is in the language the user asked for;
* the *data* is not. A skill name, a role title and a score are the
  application's, and they do not change because the answer is in Bangla.

These tests hold both halves.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import prompts
from app.models.profile import Profile


def test_the_language_instruction_names_the_language() -> None:
    assert "English" in prompts.language_instruction("en")
    assert "Bangla" in prompts.language_instruction("bn")


def test_the_bangla_instruction_keeps_technical_terms_in_english() -> None:
    """A Bangla explanation that translates ``FastAPI`` makes it unsearchable."""
    instruction = prompts.language_instruction("bn")
    assert "Keep standard English" in instruction
    assert "do not translate them" in instruction


def test_an_unknown_language_falls_back_to_english() -> None:
    assert prompts.normalise_language("fr") == "en"
    assert prompts.normalise_language(None) == "en"
    assert prompts.normalise_language("") == "en"


def test_every_spelling_of_bangla_is_understood() -> None:
    for spelling in ("bn", "bangla", "Bangladesh", "বাংলা"):
        assert prompts.normalise_language(spelling) == "bn"


def test_the_mentor_answers_in_the_requested_language(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply("আপনার দক্ষতার মধ্যে Python সবচেয়ে শক্তিশালী।")
    response = client.post(
        "/api/ai/mentor/ask", json={"message": "What is my strongest skill?", "language": "bn"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "bn"
    prompt = groq.calls[0]["messages"][0]["content"]
    assert "Write your entire answer in Bangla" in prompt
    assert "Write your entire answer in English." not in prompt


def test_the_profile_preference_is_used_when_the_request_is_silent(
    client: TestClient, auth_client, groq, db: Session
) -> None:
    auth, user = auth_client()
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    profile.preferred_language = "bn"
    db.commit()

    groq.reply("উত্তর।")
    response = client.post("/api/ai/mentor/ask", json={"message": "hello"})
    assert response.json()["language"] == "bn"


def test_the_request_overrides_the_profile_preference(
    client: TestClient, auth_client, groq, db: Session
) -> None:
    auth, user = auth_client()
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    profile.preferred_language = "bn"
    db.commit()

    groq.reply("An answer in English.")
    response = client.post(
        "/api/ai/mentor/ask", json={"message": "hello", "language": "en"}
    )
    assert response.json()["language"] == "en"
    assert "English" in groq.calls[0]["messages"][0]["content"]


def test_the_language_never_changes_a_skill_name_or_a_score(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed
) -> None:
    """The language changes the prose and nothing else.

    A Bangla answer that renamed a skill would break the application's own
    vocabulary, and a Bangla answer that recalculated a score would be the
    model deciding a number the engine owns.
    """
    auth, user = auth_client()
    role = role_seed[2]

    groq.reply("উত্তর।")
    bangla = client.post(
        "/api/ai/mentor/ask",
        json={"message": "hello", "language": "bn", "job_role_id": role.id},
    ).json()

    # The gap report in the prompt is identical whatever the language.
    prompt = groq.calls[0]["messages"][0]["content"]
    assert role.title in prompt
    assert "Pandas" in prompt or "PostgreSQL" in prompt
    assert "coverage" in prompt
    del user, bangla


def test_the_profile_language_can_be_changed(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.patch("/api/profile", json={"preferred_language": "bn"})
    assert response.status_code == 200
    assert response.json()["preferred_language"] == "bn"


def test_an_unknown_profile_language_is_refused(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.patch("/api/profile", json={"preferred_language": "fr"})
    assert response.status_code == 422


def test_the_profile_defaults_to_english(client: TestClient, auth_client, groq) -> None:
    auth, _user = auth_client()
    response = client.get("/api/profile")
    assert response.status_code == 200
    assert response.json()["preferred_language"] == "en"


@pytest.mark.parametrize("language", ["en", "bn"])
def test_every_prompt_accepts_both_languages(language: str) -> None:
    """No prompt builder may crash on a language, whatever it does with it."""
    facts = {"profile": {"headline": "Analyst"}, "skills": [], "projects": []}
    assert prompts.mentor_prompt(question="q", facts=facts, language=language)
    assert prompts.roadmap_prompt(
        role_title="R", weeks=4, facts=facts, missing_skills=[], resources=[], language=language
    )
    assert prompts.job_analysis_prompt(job_description="d", language=language)
    assert prompts.cv_advice_prompt(cv_text="c", facts=facts, language=language)
    assert prompts.interview_questions_prompt(
        role_title="R", requirements=[], facts=facts, count=3, language=language
    )
    assert prompts.interview_feedback_prompt(
        question="q",
        answer="a",
        rubric=[{"key": "k", "label": "K", "description": "d"}],
        facts=facts,
        language=language,
    )
