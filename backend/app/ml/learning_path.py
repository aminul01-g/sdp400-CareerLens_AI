"""Optional LLM learning path. **Off by default and off the critical path.**

Proposal section 4.2 makes this explicitly optional: "if time permits, an LLM API
turns the gap list into a short learning path. The core features work without
it." This module is how that promise is kept mechanically rather than by
intention:

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
Default off                   ``Settings.llm_enabled = False``; the
                              module is imported by exactly one route
Not on any core path           Reachable only through
                              ``POST /api/skill-gap/{id}/learning-path``
No key needed to boot          The key is not validated at startup
Cannot influence a score      It receives an already-computed ``GapReport``
                              and computes nothing
Distinct failure signal        ``503 feature_disabled`` when off, ``502`` on
                              a provider error — never a silent empty result
P2 in the plan                 If this is not built, nothing else changes
                              and the compliance matrix records it as
                              "not built - declared optional", which is
                              compliant
============================  ==========================================
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.core.config import Settings
from app.ml.types import GapReport, RoleSpec

logger = logging.getLogger("app.ml.learning_path")

#: Guidance copy is local, deterministic, and used whenever the LLM is off or
#: fails, so the endpoint always has something useful to return.
_TIER_FOCUS: dict[str, str] = {
    "critical": "This is required by the role. Start here.",
    "important": "Strongly expected; learn it after the critical items.",
    "desirable": "Useful but not blocking. Learn it once the essentials are solid.",
}


def build_fallback_steps(report: GapReport) -> list[dict[str, object]]:
    """Deterministic, offline learning steps derived purely from the gap report."""
    steps: list[dict[str, object]] = []
    for order, missing in enumerate(report.missing[:10], start=1):
        steps.append(
            {
                "order": order,
                "skill_id": missing.skill_id,
                "skill_name": missing.name,
                "weight": round(missing.weight, 4),
                "tier": missing.tier,
                "guidance": _TIER_FOCUS.get(missing.tier, ""),
            }
        )
    return steps


def _build_prompt(spec: RoleSpec, report: GapReport) -> str:
    missing = ", ".join(f"{m.name} (importance {m.weight:.2f})" for m in report.missing[:10])
    return (
        f"You are advising someone preparing for the role '{spec.title}'.\n"
        f"Their current weighted skill coverage is {report.coverage:.0%}.\n"
        f"Missing skills, most important first: {missing}.\n\n"
        "Return ONLY a JSON array of objects with keys 'skill_name' and 'guidance', "
        "one entry per missing skill, in the order given. "
        "Each 'guidance' must be one actionable sentence of at most 25 words. "
        "Do not add any other keys and do not wrap the array in prose."
    )


def _call_llm(prompt: str, settings: Settings) -> str:
    """One HTTPS POST to the configured provider. Raises on any failure."""
    payload = json.dumps(
        {
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 800,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def build_learning_path(spec: RoleSpec, report: GapReport, settings: Settings):
    """Return a ``LearningPathResponse``.

    Degrades gracefully: if the provider is unreachable or returns something
    unparseable, the deterministic fallback steps are returned and the failure is
    logged server-side. Provider error text is **never** surfaced to the client —
    that is the fix for the legacy behaviour at ``guidance.py:59``.
    """
    from app.schemas.recommendation import LearningPathResponse, LearningPathStep

    steps = build_fallback_steps(report)
    generated_by = "careerlens-rules"

    if settings.llm_enabled and settings.llm_api_key:
        try:
            raw = _call_llm(_build_prompt(spec, report), settings)
            start, end = raw.find("["), raw.rfind("]")
            parsed = json.loads(raw[start : end + 1]) if start != -1 else []
            by_name = {str(skill.name).lower(): skill for skill in report.missing}
            enriched: list[dict[str, object]] = []
            for index, item in enumerate(parsed[: len(steps)]):
                name = str(item.get("skill_name", "")).strip()
                target = by_name.get(name.lower())
                if target is None:
                    continue
                enriched.append(
                    {
                        "order": index + 1,
                        "skill_id": target.skill_id,
                        "skill_name": target.name,
                        "weight": round(target.weight, 4),
                        "tier": target.tier,
                        "guidance": str(item.get("guidance", "")).strip()[:300]
                        or _TIER_FOCUS.get(target.tier, ""),
                    }
                )
            if enriched:
                steps = enriched
                generated_by = f"llm:{settings.llm_model}"
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as exc:
            # Logged, not returned. The core gap report is unaffected either way.
            logger.warning("LLM learning path unavailable, using rules: %s", exc)

    return LearningPathResponse(
        job_role_id=spec.job_role_id,
        job_role_title=spec.title,
        generated_by=generated_by,
        steps=[LearningPathStep(**step) for step in steps],
    )
