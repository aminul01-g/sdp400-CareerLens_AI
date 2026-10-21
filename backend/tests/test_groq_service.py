"""The Groq client and the service that wraps it.

The provider is the one part of the system that can fail in ways nothing else
can: it can be rate limited, it can be down, it can return something the
application cannot read, and it can reject a request it used to accept. These
tests pin down what the *user* sees in each of those cases, because the rule
is that a provider problem never becomes a stack trace and never becomes a
leak of the provider's own words.

The provider is faked at the lowest level that still exercises the real code:
:func:`app.ml.groq.complete`. Everything above it — the prompt, the JSON
parse, the Pydantic validation, the error mapping — is the real thing.
"""

from __future__ import annotations

import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app.ml import groq
from app.schemas.llm import RoadmapPlanOutput, to_groq_schema

SECRET = "gsk-test-must-never-appear-in-a-response"


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #
class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


def _urlopen_returning(payload: dict):
    def _open(*args, **kwargs):
        return _Response(payload)

    return _open


def _urlopen_raising(error: BaseException):
    def _open(*args, **kwargs):
        raise error

    return _open


def test_a_missing_key_is_a_configuration_error_not_a_request() -> None:
    with pytest.raises(groq.GroqConfigError):
        groq.complete([{"role": "user", "content": "hi"}], api_key="")


def test_a_successful_call_returns_the_assistants_text(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_returning({"choices": [{"message": {"content": "hello"}}]}),
    )
    text = groq.complete(
        [{"role": "user", "content": "hi"}],
        api_key=SECRET,
        model="openai/gpt-oss-120b",
    )
    assert text == "hello"


def test_the_reasoning_parameters_are_only_sent_to_models_that_understand_them(
    monkeypatch,
) -> None:
    """A 400 for an unknown parameter is indistinguishable from a 400 for a bad
    schema when the provider's message is not surfaced, so the parameters are
    emitted only where Groq documents them."""
    sent: list[dict] = []

    def _open(request, timeout=None):
        sent.append(json.loads(request.data.decode("utf-8")))
        return _Response({"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr(urllib.request, "urlopen", _open)

    groq.complete(
        [{"role": "user", "content": "hi"}],
        api_key=SECRET,
        model="openai/gpt-oss-120b",
        reasoning_effort="medium",
    )
    groq.complete([{"role": "user", "content": "hi"}], api_key=SECRET, model="some/other-model")

    assert sent[0]["include_reasoning"] is False
    assert sent[0]["reasoning_effort"] == "medium"
    assert "include_reasoning" not in sent[1]
    assert "reasoning_effort" not in sent[1]


def test_a_rate_limit_is_reported_as_a_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_raising(urllib.error.HTTPError("u", 429, "slow down", {}, None)),
    )
    with pytest.raises(groq.GroqRateLimitedError):
        groq.complete(
            [{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=0
        )


def test_a_rejected_credential_is_reported_as_such(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_raising(urllib.error.HTTPError("u", 401, "bad key", {}, None)),
    )
    with pytest.raises(groq.GroqAuthenticationError):
        groq.complete(
            [{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=0
        )


def test_a_provider_failure_is_not_retried_when_it_cannot_help(monkeypatch) -> None:
    """Retrying a bad request produces the same bad request, and costs money."""
    calls: list[int] = []

    def _open(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("u", 400, "bad schema", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    with pytest.raises(groq.GroqInvalidRequestError):
        groq.complete(
            [{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=3
        )
    assert len(calls) == 1


def test_a_transient_failure_is_retried_within_the_ceiling(monkeypatch) -> None:
    calls: list[int] = []

    def _open(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("u", 503, "unavailable", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    with pytest.raises(groq.GroqServerError):
        groq.complete(
            [{"role": "user", "content": "hi"}],
            api_key=SECRET,
            max_retries=2,
            backoff_seconds=0,
        )
    assert len(calls) == 3, "one attempt plus two retries"


def test_a_body_that_is_not_json_is_an_invalid_response(monkeypatch) -> None:
    class _Bad(_Response):
        def read(self) -> bytes:
            return b"<html>gateway error</html>"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Bad({}))
    with pytest.raises(groq.GroqInvalidResponseError):
        groq.complete([{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=0)


def test_the_key_is_never_in_an_error_message(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_raising(urllib.error.HTTPError("u", 401, "bad key", {}, None)),
    )
    with pytest.raises(groq.GroqAuthenticationError) as caught:
        groq.complete([{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=0)
    assert SECRET not in str(caught.value)


# --------------------------------------------------------------------------- #
# The strict-mode schema
# --------------------------------------------------------------------------- #
def test_the_rendered_schema_is_closed_and_fully_required() -> None:
    """Strict mode rejects anything else, and the provider is told so."""
    schema = to_groq_schema(RoadmapPlanOutput)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for name, sub in schema["properties"].items():
        if sub.get("type") == "object" or "properties" in sub:
            assert sub["additionalProperties"] is False, name
            assert set(sub["required"]) == set(sub["properties"]), name


def test_the_rendered_schema_has_no_defs_to_resolve() -> None:
    schema = to_groq_schema(RoadmapPlanOutput)
    assert "$defs" not in schema
    assert "$ref" not in json.dumps(schema)


# --------------------------------------------------------------------------- #
# The service
# --------------------------------------------------------------------------- #
def test_the_ai_status_endpoint_reports_whether_the_provider_is_configured(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["model"] == "openai/gpt-oss-120b"
    assert "mentor" in body["features"]


def test_the_ai_status_endpoint_never_leaks_the_key(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.get("/api/ai/status")
    assert "test-key-not-a-real-credential" not in response.text


def test_an_unconfigured_deployment_reports_the_ai_layer_as_off(
    client: TestClient, auth_client, groq_disabled
) -> None:
    auth, _user = auth_client()
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["model"] == ""
    assert body["features"] == []


def test_an_unconfigured_deployment_answers_503_on_every_ai_route(
    client: TestClient, auth_client, groq_disabled
) -> None:
    """The AI layer is an enhancement, and this is what "off" means.

    The routes that *generate* something answer 503. The routes that read the
    user's own saved artefacts keep working, because a learner with a saved
    plan should still be able to open it on a deployment whose provider has
    been switched off.
    """
    auth, _user = auth_client()
    for path, method, payload in (
        ("/api/ai/mentor/ask", "post", {"message": "hello"}),
        ("/api/ai/roadmaps", "post", {"job_role_id": 1, "duration_weeks": 4}),
        ("/api/ai/job-analysis", "post", {"job_description": "x" * 400}),
        ("/api/ai/cv-advice", "post", {"cv_text": "x" * 400}),
        ("/api/ai/interviews", "post", {"job_role_id": 1}),
    ):
        response = getattr(client, method)(path, json=payload)
        assert response.status_code == 503, path
        assert response.json()["error"]["code"] == "feature_disabled", path


def test_the_core_features_work_with_no_provider_configured(
    client: TestClient, auth_client, groq_disabled
) -> None:
    """The promise the whole design rests on: no provider, no core features."""
    auth, _user = auth_client()
    assert client.get("/api/dashboard/summary").status_code == 200
    assert client.get("/api/skills").status_code == 200
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/cv").status_code == 200


def test_reading_a_saved_plan_is_not_rate_limited(
    client: TestClient, auth_client, groq, role_seed, taxonomy_seed, monkeypatch
) -> None:
    """The AI rate limit exists to bound the provider's bill.

    A learner coming back to a saved plan, ticking a task off or writing a
    note costs nothing, and must never be told to wait for the generation
    limit to clear.
    """
    from app.api.deps import rate_limit

    checked: list[str] = []

    original = rate_limit("ai")

    def _spy():
        checked.append("ai")
        return original()

    monkeypatch.setattr("app.api.routes.roadmap.rate_limit", _spy, raising=False)

    auth, _user = auth_client()
    role = role_seed[2]
    groq.reply_json(
        {
            "target_role": role.title,
            "starting_profile": "",
            "strengths": [],
            "skill_gaps": [],
            "learning_objectives": [],
            "tasks": [
                {
                    "week": 1,
                    "title": "Do the thing",
                    "objective": "",
                    "activities": [],
                    "deliverable": "",
                    "completion_criteria": [],
                    "estimated_hours": 1.0,
                    "skill_name": "",
                    "resource_ids": [],
                    "portfolio_hint": "",
                }
            ],
            "portfolio_project": {
                "title": "p",
                "problem_statement": "",
                "required_technologies": [],
                "milestones": [],
                "expected_outputs": [],
                "evaluation_criteria": [],
                "demonstrates_skills": [],
            },
            "portfolio_presentation": [],
            "total_estimated_hours": 1.0,
            "notes": "",
        }
    )
    created = client.post(
        "/api/ai/roadmaps", json={"job_role_id": role.id, "duration_weeks": 4}
    ).json()
    assert created["id"]

    before = len(checked)
    assert client.get("/api/ai/roadmaps").status_code == 200
    assert client.get(f"/api/ai/roadmaps/{created['id']}").status_code == 200
    assert (
        client.patch(
            f"/api/ai/roadmaps/{created['id']}/tasks/{created['tasks'][0]['task_key']}",
            json={"is_complete": True},
        ).status_code
        == 200
    )
    assert client.delete(f"/api/ai/roadmaps/{created['id']}").status_code == 204
    assert len(checked) == before, "a read or a progress update was rate limited"


def test_the_request_carries_a_user_agent(monkeypatch) -> None:
    """The provider's edge rejects the standard library's default agent.

    ``Python-urllib/3.12`` is answered with ``403`` and ``error code:
    1010`` -- the edge's "your signature is banned" response -- however
    valid the request is. The agent below identifies the application, which
    is what the edge wants to see. This test exists because the failure is
    invisible to a mocked suite: everything else about the request is
    correct, and the only thing wrong is a header.
    """
    sent: list[dict] = []

    def _open(request, timeout=None):
        sent.append({k.lower(): v for k, v in request.header_items()})
        return _Response({"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    groq.complete([{"role": "user", "content": "hi"}], api_key=SECRET)
    assert sent
    assert sent[0].get("user-agent") == groq.USER_AGENT
    assert "Python-urllib" not in sent[0].get("user-agent", "")


def test_a_rate_limit_is_not_retried(monkeypatch) -> None:
    """The provider's quota is per organisation, not per request.

    Another attempt a fraction of a second later is rejected for the same
    reason, so retrying it burns the allowance and delays the 429 the
    caller should have been told about straight away.
    """
    calls: list[int] = []

    def _open(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("u", 429, "slow down", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    with pytest.raises(groq.GroqRateLimitedError):
        groq.complete(
            [{"role": "user", "content": "hi"}], api_key=SECRET, max_retries=3
        )
    assert len(calls) == 1, "a rate limit was retried"


def test_a_transient_server_error_is_still_retried(monkeypatch) -> None:
    """A 503 is worth another attempt; a 429 is not."""
    calls: list[int] = []

    def _open(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("u", 503, "unavailable", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _open)
    with pytest.raises(groq.GroqServerError):
        groq.complete(
            [{"role": "user", "content": "hi"}],
            api_key=SECRET,
            max_retries=2,
            backoff_seconds=0,
        )
    assert len(calls) == 3


def test_a_single_element_array_wrapping_the_object_is_unwrapped(monkeypatch) -> None:
    """Observed against the live provider, not imagined.

    A schema-constrained response occasionally arrives as a one-element array
    around the object. There is no reading of a one-element list of objects
    that means anything else, so it is unwrapped; anything else is still
    refused.
    """
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_returning(
            {"choices": [{"message": {"content": json.dumps([{"role_title": "Data Analyst"}])}}]}
        ),
    )
    parsed = groq.complete_json(
        [{"role": "user", "content": "x"}],
        json_schema={"type": "object"},
        api_key=SECRET,
    )
    assert parsed == {"role_title": "Data Analyst"}


def test_a_list_of_several_objects_is_still_refused(monkeypatch) -> None:
    """The unwrapping is for the wrapper, not for lists in general."""
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_returning(
            {"choices": [{"message": {"content": json.dumps([{"a": 1}, {"b": 2}])}}]}
        ),
    )
    with pytest.raises(groq.GroqInvalidResponseError):
        groq.complete_json(
            [{"role": "user", "content": "x"}],
            json_schema={"type": "object"},
            api_key=SECRET,
        )


def test_the_provider_error_code_is_kept_for_diagnosis(monkeypatch) -> None:
    """The code, never the message.

    The message of a schema failure contains the generated output, and the
    generated output can echo the user's document. The code says what went
    wrong without saying what was sent.
    """

    class _JsonError(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("u", 400, "bad", {}, None)

        def read(self):
            return json.dumps(
                {
                    "error": {
                        "message": "Generated JSON does not match ... secret cv text",
                        "code": "json_validate_failed",
                    }
                }
            ).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(_JsonError()))
    with pytest.raises(groq.GroqInvalidRequestError) as caught:
        groq.complete([{"role": "user", "content": "x"}], api_key=SECRET, max_retries=0)
    assert "json_validate_failed" in str(caught.value)
    assert "secret cv text" not in str(caught.value)


def test_a_structured_answer_that_does_not_fit_is_retried_once(client, groq) -> None:
    """The provider's own message for this case is "please adjust your prompt".

    So the adjustment is made: the output-shape rule is added to the prompt
    and the request is sent again, exactly once. A provider that is
    consistently wrong costs one extra call and then a clean error.
    """
    from app.schemas.llm import JobAnalysisOutput
    from app.services.groq_service import run_structured

    # The first answer is the single-element array wrapper, which the client
    # unwraps into an object that is missing every required field.
    groq.reply_json({"role_title": "Data Analyst"})
    groq.reply_json(
        {
            "role_title": "Data Analyst",
            "summary": "s",
            "required_skills": [],
            "preferred_skills": [],
            "tools_and_technologies": [],
            "experience_requirement": "",
            "education_requirement": "",
            "responsibilities": [],
            "deliverables": [],
            "limitations": [],
        }
    )
    result = run_structured(
        [{"role": "user", "content": "read this"}], JobAnalysisOutput
    )
    assert result.role_title == "Data Analyst"
    assert len(groq.calls) == 2, "the request was not retried"


def test_a_persistent_schema_failure_is_a_clean_422(client, groq) -> None:
    """After the bounded retry, the caller gets a clean error, not a stack trace."""
    from app.core.exceptions import UnprocessableError
    from app.schemas.llm import JobAnalysisOutput
    from app.services.groq_service import run_structured

    groq.reply_json({"role_title": "Data Analyst"})
    groq.reply_json({"role_title": "Data Analyst"})
    with pytest.raises(UnprocessableError) as caught:
        run_structured([{"role": "user", "content": "read this"}], JobAnalysisOutput)
    assert caught.value.status_code == 422
    assert len(groq.calls) == 2, "the retry was not bounded"
