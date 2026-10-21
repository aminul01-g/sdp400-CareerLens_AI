"""Optional LLM learning path. **Off by default and off the critical path.**

Proposal section 4.2 makes this explicitly optional: "if time permits, an LLM API
turns the gap list into a short learning path. The core features work without
it." This module is how that promise is kept mechanically rather than by
intention:

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
Default off                   ``Settings.llm_enabled = False``; the flag is
                              checked in the route, not here
Not on any core path           Reachable only through
                              ``POST /api/skill-gap/{id}/learning-path``
No key needed to boot          Nothing here reads configuration at import
Cannot influence a score      It receives an already-computed ``GapReport``
                              and computes nothing
Pure module                    Imports only ``app.ml.types``,
                               ``app.ml.groq`` and the standard library, so
                               it inherits the ML layer's no-ORM /
                               no-framework guarantee. Provider credentials
                               arrive as plain arguments, and the Pydantic
                               response model is built by the route

Distinct failure signal        ``503 feature_disabled`` when off, and a
                              logged fallback on provider failure — never a
                              silent empty result
P2 in the plan                 Not building this is compliant; the matrix
                              would record it as "not built - declared
                              optional"
============================  ==========================================
"""

from __future__ import annotations

import json
import logging

from app.ml import groq
from app.ml.types import GapReport, RoleSpec

logger = logging.getLogger("app.ml.learning_path")

#: Guidance copy is local, deterministic, and used whenever the LLM is unavailable,
#: so the endpoint always returns something useful.
TIER_FOCUS: dict[str, str] = {
    "critical": "Required by the role. Start here.",
    "important": "Strongly expected; learn it after the critical items.",
    "desirable": "Useful but not blocking. Learn it once the essentials are solid.",
}

MAX_STEPS = 10
MAX_GUIDANCE_CHARS = 300


def build_fallback_steps(report: GapReport) -> list[dict[str, object]]:
    """Deterministic, offline learning steps derived purely from the gap report.

    The gap is already sorted by descending importance weight, so the first step is
    the single most valuable thing to learn next. This function computes nothing
    new; it only renders what the gap analysis already decided.
    """
    steps: list[dict[str, object]] = []
    for order, missing in enumerate(report.missing[:MAX_STEPS], start=1):
        steps.append(
            {
                "order": order,
                "skill_id": missing.skill_id,
                "skill_name": missing.name,
                "weight": round(missing.weight, 4),
                "tier": missing.tier,
                "guidance": TIER_FOCUS.get(missing.tier, ""),
            }
        )
    return steps


def build_prompt(spec: RoleSpec, report: GapReport) -> str:
    """The instruction sent to the provider. Deterministic; no user text is echoed."""
    missing = ", ".join(f"{m.name} (importance {m.weight:.2f})" for m in report.missing[:MAX_STEPS])
    return (
        f"You are advising someone preparing for the role '{spec.title}'.\n"
        f"Their current weighted skill coverage is {report.coverage:.0%}.\n"
        f"Missing skills, most important first: {missing}.\n\n"
        "Return ONLY a JSON array of objects with keys 'skill_name' and 'guidance', "
        "one entry per missing skill, in the order given. "
        "Each 'guidance' must be one actionable sentence of at most 25 words. "
        "Do not add any other keys and do not wrap the array in prose."
    )


def _call_provider(
    prompt: str, *, api_key: str, model: str, base_url: str, timeout: int
) -> str:
    """One provider call, through the shared client.

    The HTTP itself lives in :mod:`app.ml.groq` so that the application has
    exactly one place that reaches the network. This function is the narrow
    seam between that client and the learning-path logic: it sends the prompt
    and returns the assistant's text, and raises
    :class:`app.ml.groq.GroqError` on any failure.
    """
    return groq.complete(
        [{"role": "user", "content": prompt}],
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        # One attempt. The caller degrades to the deterministic steps, and a
        # second attempt would only slow that down.
        max_retries=0,
        temperature=0.3,
        max_completion_tokens=800,
    )


def _parse_provider_output(raw: str, report: GapReport) -> list[dict[str, object]]:
    """Map provider prose onto the already-computed gap.

    The weight, tier and skill id are taken from ``report``, never from the model's
    text, so a hallucinated weight or a reordered list cannot corrupt the output.
    """
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    by_name = {skill.name.strip().lower(): skill for skill in report.missing}
    steps: list[dict[str, object]] = []
    for item in parsed[:MAX_STEPS]:
        if not isinstance(item, dict):
            continue
        target = by_name.get(str(item.get("skill_name", "")).strip().lower())
        if target is None:
            # A skill we did not identify as missing is discarded rather than
            # invented into the result.
            continue
        guidance = str(item.get("guidance", "")).strip()[:MAX_GUIDANCE_CHARS]
        steps.append(
            {
                "order": len(steps) + 1,
                "skill_id": target.skill_id,
                "skill_name": target.name,
                "weight": round(target.weight, 4),
                "tier": target.tier,
                "guidance": guidance or TIER_FOCUS.get(target.tier, ""),
            }
        )
    return steps


def build_learning_path(
    spec: RoleSpec,
    report: GapReport,
    *,
    api_key: str = "",
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    timeout: int = 20,
) -> tuple[list[dict[str, object]], str]:
    """Return ``(steps, generated_by)``.

    Degrades gracefully. If the provider is unreachable, slow, or returns something
    unparseable, the deterministic fallback steps are returned and the failure is
    logged **server-side only** — provider error text never reaches the client,
    which is the fix for the legacy behaviour at ``guidance.py:59``.

    With no API key the LLM branch is skipped entirely, so the core system never
    depends on one.
    """
    fallback = build_fallback_steps(report)
    if not api_key or not fallback:
        return fallback, "careerlens-rules"

    try:
        raw = _call_provider(
            build_prompt(spec, report),
            api_key=api_key, model=model, base_url=base_url, timeout=timeout,
        )
    except (groq.GroqError, KeyError, ValueError, OSError) as exc:
        logger.warning("LLM learning path unavailable; using the deterministic steps: %s", exc)
        return fallback, "careerlens-rules"

    enriched = _parse_provider_output(raw, report)
    if enriched:
        return enriched, f"llm:{model}"
    logger.warning("LLM returned no usable learning steps; using the deterministic ones")
    return fallback, "careerlens-rules"

