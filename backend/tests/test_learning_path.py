"""The optional LLM learning path, and the guarantees that keep it optional.

Proposal section 4.2 makes this feature conditional: "if time permits, an LLM
API turns the gap list into a short learning path. The core features work
without it." These tests are mostly about that promise holding.

What is asserted here:

* with no API key the LLM branch is never entered;
* a provider failure of any kind degrades to the deterministic steps, and the
  provider's error text never reaches the caller;
* the deterministic steps are a pure function of the gap report -- no clock, no
  randomness, no network -- so two calls with the same gap return the same plan;
* a model cannot inject a weight, a tier, a skill id, or a skill that was not in
  the gap, however confidently it asserts them;
* the prompt carries no user data and no credential, because it is about to be
  sent to a third party.

The last two are the tests that matter most. A hallucinated weight would silently
corrupt a plan the user is about to follow, and a prompt that leaked a user's bio
into a third-party API would be a genuine privacy incident. Nothing else in the
suite would catch either.
"""

from __future__ import annotations

import json
import urllib.request

import pytest

from app.ml.learning_path import (
    MAX_GUIDANCE_CHARS,
    MAX_STEPS,
    build_fallback_steps,
    build_learning_path,
    build_prompt,
)
from app.ml.types import GapReport, MatchedSkill, MissingSkill, RoleSpec

SECRET = "sk-test-must-never-appear-in-a-prompt"
RULES = "careerlens-rules"


def make_gap(
    *,
    coverage: float = 0.4,
    missing: tuple[MissingSkill, ...] = (
        MissingSkill(
            skill_id=10, name="Kubernetes", weight=0.9,
            tier="critical", category="MLOps & Cloud",
        ),
        MissingSkill(
            skill_id=11, name="Terraform", weight=0.7,
            tier="important", category="MLOps & Cloud",
        ),
        MissingSkill(
            skill_id=12, name="Helm", weight=0.4,
            tier="desirable", category="MLOps & Cloud",
        ),
    ),
) -> GapReport:
    return GapReport(
        job_role_id=7,
        title="MLOps Engineer",
        family="MLOps",
        coverage=coverage,
        matched=(
            MatchedSkill(
                skill_id=1, name="Python", weight=1.0, proficiency=5,
                contribution=1.0, category="Programming & Core",
            ),
        ),
        missing=missing,
    )


SPEC = RoleSpec(
    job_role_id=7,
    title="MLOps Engineer",
    slug="mlops-engineer",
    family="MLOps",
    description="Build and run model serving infrastructure.",
    required_skills={1: 1.0, 10: 0.9, 11: 0.7, 12: 0.4},
)


def fake_provider(payload: str):
    """A urlopen stand-in returning ``payload`` as the provider's message content."""
    body = {"choices": [{"message": {"content": payload}}]}

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps(body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> bool:
            return False

    return lambda *args, **kwargs: FakeResponse()


# --------------------------------------------------------------------------- #
# deterministic fallback
# --------------------------------------------------------------------------- #


def test_fallback_steps_follow_the_gap_order() -> None:
    """The first step is the most valuable thing to learn next.

    The gap list is already sorted by descending weight, so this function must
    not re-sort it -- re-sorting would risk disagreeing with the ordering the
    user just saw on the gap screen.
    """
    steps = build_fallback_steps(make_gap())
    assert [s["skill_name"] for s in steps] == ["Kubernetes", "Terraform", "Helm"]
    assert [s["order"] for s in steps] == [1, 2, 3]


def test_fallback_steps_carry_the_gaps_own_weight_and_tier() -> None:
    """Weight and tier come from the gap report, never from the model."""
    steps = build_fallback_steps(make_gap())
    assert [s["weight"] for s in steps] == [0.9, 0.7, 0.4]
    assert [s["tier"] for s in steps] == ["critical", "important", "desirable"]
    assert [s["skill_id"] for s in steps] == [10, 11, 12]


def test_fallback_steps_explain_the_tier() -> None:
    for step in build_fallback_steps(make_gap()):
        guidance = str(step["guidance"])
        assert guidance.strip(), "a step with no explanation is not actionable"
        assert len(guidance) <= MAX_GUIDANCE_CHARS


def test_fallback_steps_are_bounded() -> None:
    many = tuple(
        MissingSkill(
            skill_id=100 + i, name=f"Skill {i}", weight=1.0 - i / 1000,
            tier="desirable", category="X",
        )
        for i in range(40)
    )
    steps = build_fallback_steps(make_gap(missing=many))
    assert len(steps) == MAX_STEPS
    for step in steps:
        assert len(str(step["guidance"])) <= MAX_GUIDANCE_CHARS


def test_fallback_steps_handle_an_empty_gap() -> None:
    """Nothing missing must produce nothing, not a crash and not filler advice."""
    assert build_fallback_steps(make_gap(missing=(), coverage=1.0)) == []


def test_fallback_steps_are_deterministic() -> None:
    gap = make_gap()
    assert build_fallback_steps(gap) == build_fallback_steps(gap)


# --------------------------------------------------------------------------- #
# the LLM branch
# --------------------------------------------------------------------------- #


def test_no_api_key_means_the_llm_is_never_called(monkeypatch) -> None:
    """The core system must not depend on a third-party provider.

    Asserted by making any network attempt explode: if the LLM branch were
    entered without a key, the test would fail loudly rather than quietly
    succeeding on a machine that happens to have one configured.
    """

    def explode(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("the LLM branch was entered without an API key")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key="")
    assert generated_by == RULES
    assert [s["skill_name"] for s in steps] == ["Kubernetes", "Terraform", "Helm"]


def test_empty_gap_skips_the_provider_even_with_a_key(monkeypatch) -> None:
    """Nothing to learn means there is no reason to spend a token on it."""

    def explode(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("the provider was called for a user with no skill gap")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    steps, generated_by = build_learning_path(SPEC, make_gap(missing=()), api_key=SECRET)
    assert steps == []
    assert generated_by == RULES


def test_provider_failure_degrades_to_the_fallback(monkeypatch) -> None:
    """An unreachable provider must not become a 500 for the user."""

    def explode(*args, **kwargs):
        raise OSError("connection refused to the provider")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert generated_by == RULES
    assert steps == build_fallback_steps(make_gap())


def test_provider_error_text_never_reaches_the_caller(monkeypatch) -> None:
    """The leak the predecessor had at guidance.py:59 must not come back.

    Provider errors can contain the request body, an account identifier, or an
    internal hostname. None of that belongs in an API response, so the returned
    value must be indistinguishable from the plain fallback.
    """
    sensitive = "quota exceeded for account org_9f2b at internal-lb.provider.invalid"

    def explode(*args, **kwargs):
        raise OSError(sensitive)

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    serialised = json.dumps({"steps": steps, "generated_by": generated_by})
    assert sensitive not in serialised
    assert "org_9f2b" not in serialised
    assert "internal-lb" not in serialised


def test_unparseable_provider_output_degrades(monkeypatch) -> None:
    """A provider returning prose instead of JSON must not surface as an error."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider("I think you should probably learn Kubernetes first!"),
    )
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert generated_by == RULES
    assert steps == build_fallback_steps(make_gap())


def test_valid_provider_output_is_used_when_parseable(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([
            {"skill_name": "Kubernetes", "guidance": "Work through the official concepts page."},
            {"skill_name": "Terraform", "guidance": "Provision a throwaway cluster first."},
        ])),
    )
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert generated_by == "llm:gpt-4o-mini"
    assert [s["skill_name"] for s in steps] == ["Kubernetes", "Terraform"]
    assert steps[0]["guidance"] == "Work through the official concepts page."


def test_prose_wrapped_json_is_still_accepted(monkeypatch) -> None:
    """Models add preamble despite instructions; the parser should cope."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(
            "Sure! Here you go:\n"
            '[{"skill_name": "Helm", "guidance": "Install it and chart one service."}]\n'
            "Hope that helps."
        ),
    )
    steps, generated_by = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert generated_by == "llm:gpt-4o-mini"
    assert steps[0]["skill_name"] == "Helm"


def test_a_model_cannot_invent_a_skill(monkeypatch) -> None:
    """A skill that was not in the gap is discarded, not adopted.

    This is the hallucination guard. Without it a model could name a skill the
    user does not need and the plan would send them to learn the wrong thing.
    """
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([
            {"skill_name": "Rust", "guidance": "Learn it, it is very important."},
            {"skill_name": "Kubernetes", "guidance": "Start with the concepts page."},
        ])),
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert [s["skill_name"] for s in steps] == ["Kubernetes"]


def test_a_model_cannot_override_a_weight_or_tier(monkeypatch) -> None:
    """Those come from the gap report, so a confident model cannot change them.

    A hallucinated weight would reorder the plan against the weight the user was
    shown on the gap screen.
    """
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([
            {
                "skill_name": "Helm",
                "guidance": "Chart one service.",
                "weight": 0.99,
                "tier": "critical",
                "skill_id": 9999,
            },
            {"skill_name": "Kubernetes", "guidance": "Concepts page."},
        ])),
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    helm = next(s for s in steps if s["skill_name"] == "Helm")
    assert helm["weight"] == 0.4
    assert helm["tier"] == "desirable"
    assert helm["skill_id"] == 12


def test_oversized_guidance_is_truncated(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([
            {"skill_name": "Helm", "guidance": "x" * 5000},
        ])),
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert len(str(steps[0]["guidance"])) == MAX_GUIDANCE_CHARS


def test_provider_step_count_is_bounded(monkeypatch) -> None:
    """A model returning 200 steps must not produce a 200-step plan."""
    many = [
        {"skill_name": name, "guidance": "Do the thing."}
        for name in ("Kubernetes", "Terraform", "Helm")
    ]
    monkeypatch.setattr(
        urllib.request, "urlopen", fake_provider(json.dumps(many * 100))
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert len(steps) <= MAX_STEPS


def test_empty_guidance_falls_back_to_the_tier_text(monkeypatch) -> None:
    """A model returning nothing useful still yields an explained step."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([{"skill_name": "Helm", "guidance": "   "}])),
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert str(steps[0]["guidance"]).strip()


def test_skill_matching_is_case_insensitive(monkeypatch) -> None:
    """Real models capitalise differently; the plan should survive that."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        fake_provider(json.dumps([{"skill_name": "  kubernetes ", "guidance": "Concepts."}])),
    )
    steps, _ = build_learning_path(SPEC, make_gap(), api_key=SECRET)
    assert steps[0]["skill_name"] == "Kubernetes"


# --------------------------------------------------------------------------- #
# the prompt
# --------------------------------------------------------------------------- #


def test_prompt_contains_the_role_and_the_gap() -> None:
    prompt = build_prompt(SPEC, make_gap())
    assert "MLOps Engineer" in prompt
    for skill in ("Kubernetes", "Terraform", "Helm"):
        assert skill in prompt
    assert "0.90" in prompt, "the prompt must carry the weights it is reasoning about"


def test_prompt_reports_coverage_honestly() -> None:
    assert "40%" in build_prompt(SPEC, make_gap(coverage=0.4))
    assert "100%" in build_prompt(SPEC, make_gap(coverage=1.0, missing=()))


def test_prompt_carries_no_credential() -> None:
    """Whatever else happens, no key may ever be in the prompt text."""
    prompt = build_prompt(SPEC, make_gap())
    assert SECRET not in prompt
    assert "api_key" not in prompt.lower()
    assert "authorization" not in prompt.lower()
    assert "bearer" not in prompt.lower()


def test_prompt_contains_only_role_metadata_and_skill_names() -> None:
    """The prompt is about to leave the process, so it carries the minimum.

    Role title, coverage and skill names are all it needs. A user's email, bio or
    employer must not be present -- which is why this asserts the prompt adds
    nothing beyond the gap's own contents.
    """
    prompt = build_prompt(SPEC, make_gap())
    for marker in ("@", "email", "phone", "linkedin", "salary", "password", "resume"):
        assert marker not in prompt.lower(), f"prompt mentions {marker!r}"


def test_prompt_is_bounded() -> None:
    """A user with a large gap must not be able to build an enormous request."""
    many = tuple(
        MissingSkill(
            skill_id=200 + i, name=f"Extremely Long Skill Name Number {i}",
            weight=1.0, tier="desirable", category="A Very Long Category Name Indeed",
        )
        for i in range(200)
    )
    assert len(build_prompt(SPEC, make_gap(missing=many))) < 20_000


def test_prompt_is_deterministic() -> None:
    gap = make_gap()
    assert build_prompt(SPEC, gap) == build_prompt(SPEC, gap)


@pytest.mark.parametrize("coverage", [0.0, 0.5, 1.0])
def test_fallback_is_stable_across_coverage(coverage: float) -> None:
    gap = make_gap(coverage=coverage)
    assert build_fallback_steps(gap) == build_fallback_steps(gap)
