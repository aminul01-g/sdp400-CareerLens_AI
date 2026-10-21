"""The one service every AI feature goes through.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
One call site                 Every model call in the application is made
                               from this module. A feature that wanted its
                               own HTTP client would have to bypass this
                               file, and the compliance script checks that
                               it does not
Optional by construction      With no API key, :func:`require_provider`
                               raises a 503 and the caller never reaches the
                               provider. The core features — CV processing,
                               matching, gap analysis — never call this
                               module at all
Validated before it is used   A structured answer is parsed into a Pydantic
                               model before it is displayed or written to
                               the database. A shape the application did not
                               ask for is refused, not coerced
Provider text stays internal  Every provider failure is mapped onto one of
                               the application's own error types. The
                               provider's message, its body and its
                               credential never reach the client
============================  ==========================================
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    FeatureDisabledError,
    TooManyRequestsError,
    UnprocessableError,
    UpstreamError,
)
from app.ml import groq
from app.schemas.llm import to_groq_schema

logger = logging.getLogger("app.services.groq")

ModelT = TypeVar("ModelT", bound=BaseModel)

#: The name the provider shows in its own logs for a structured request.
DEFAULT_SCHEMA_NAME = "careerlens_response"


def ai_is_available(settings: Settings | None = None) -> bool:
    """Whether the AI layer is configured and can be used."""
    resolved = settings or get_settings()
    return resolved.groq_is_configured


def require_provider(settings: Settings | None = None) -> Settings:
    """Return the settings, or refuse if the provider is not usable.

    The refusal is a 503 with the same ``feature_disabled`` code the
    application already uses for the optional learning path, so the frontend
    has one "this deployment has no AI" path rather than two.
    """
    resolved = settings or get_settings()
    if not resolved.groq_is_configured:
        raise FeatureDisabledError(
            "The AI assistant is not enabled on this deployment. Everything else "
            "in CareerLens — CV analysis, career matching and skill-gap analysis — "
            "works without it. Set GROQ_API_KEY to turn it on."
        )
    return resolved


def _translate(exc: Exception) -> Exception:
    """Map a provider failure onto the application's own error type.

    Nothing from the provider survives this function except the fact that
    something went wrong and, for a rate limit, how long to wait.
    """
    if isinstance(exc, groq.GroqRateLimitedError):
        return TooManyRequestsError(
            "The AI service is busy right now. Please wait a moment and try again.",
            retry_after=30,
        )
    if isinstance(exc, groq.GroqInvalidRequestError):
        # A schema the provider refused is our fault, not the caller's, so it
        # is reported as a server-side problem rather than a bad request.
        logger.error("AI provider rejected a request as invalid", extra={"kind": "ai"})
        return UpstreamError(
            "The AI service could not process that request. Please try again."
        )
    if isinstance(exc, groq.GroqAuthenticationError):
        logger.error("AI provider rejected the configured credential", extra={"kind": "ai"})
        return UpstreamError(
            "The AI service is not configured correctly on this deployment. "
            "Please try again later."
        )
    if isinstance(exc, groq.GroqInvalidResponseError):
        logger.warning("AI provider returned an unusable response", extra={"kind": "ai"})
        return UnprocessableError(
            "The AI service returned an answer this application could not read. "
            "Please try again."
        )
    if isinstance(exc, groq.GroqConfigError):
        return FeatureDisabledError(
            "The AI assistant is not enabled on this deployment. Everything else "
            "in CareerLens works without it."
        )
    if isinstance(exc, groq.GroqError):
        logger.warning("AI provider unavailable: %s", type(exc).__name__, extra={"kind": "ai"})
        return UpstreamError()
    return UpstreamError()


def run_chat(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    temperature: float = 0.6,
    reasoning_effort: str = "medium",
    max_completion_tokens: int = 3000,
) -> str:
    """Ask the provider for prose and return it.

    Used by the career mentor, where the answer is a human-readable
    explanation rather than a document to store.

    The completion budget is generous because the model's reasoning tokens
    come out of the same allowance as the answer: a 2 000-token cap is
    enough for a short reply and too tight for a considered one, and a
    truncated answer ends mid-sentence with no sign that it was cut.
    """
    resolved = require_provider(settings)
    try:
        return groq.complete(
            messages,
            api_key=resolved.provider_api_key,
            model=resolved.provider_model,
            base_url=resolved.provider_base_url,
            timeout=resolved.provider_timeout_seconds,
            max_retries=resolved.groq_max_retries,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            max_completion_tokens=max_completion_tokens,
        )
    except Exception as exc:
        raise _translate(exc) from exc


def run_structured(
    messages: list[dict[str, str]],
    model: type[ModelT],
    *,
    schema_name: str = DEFAULT_SCHEMA_NAME,
    settings: Settings | None = None,
    temperature: float = 0.4,
    reasoning_effort: str = "medium",
    max_completion_tokens: int = 4000,
    attempts: int = 2,
) -> ModelT:
    """Ask the provider for a document and validate it.

    The schema is derived from the Pydantic model, so the two cannot drift:
    a field added to the model is a field the provider is told to produce, and
    a field the provider invents is a field validation rejects.

    A structured answer that does not match the requested shape is retried
    **once**, with the output-shape rule added to the prompt. The provider's
    own error message for this case is "please adjust your prompt", and the
    adjustment is known: the response occasionally arrives as a single-element
    array wrapping the object. The retry is bounded, so a provider that is
    consistently wrong costs one extra call and then a clean error.
    """
    resolved = require_provider(settings)
    schema = to_groq_schema(model)
    last_failure: Exception | None = None

    for attempt in range(max(1, attempts)):
        try:
            raw = groq.complete_json(
                messages,
                json_schema=schema,
                schema_name=schema_name,
                api_key=resolved.provider_api_key,
                model=resolved.provider_model,
                base_url=resolved.provider_base_url,
                timeout=resolved.provider_timeout_seconds,
                max_retries=resolved.groq_max_retries,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_completion_tokens=max_completion_tokens,
            )
        except groq.GroqInvalidRequestError as exc:
            last_failure = exc
            if attempt + 1 < attempts and "json_validate_failed" in str(exc):
                messages = _with_output_rule(messages)
                continue
            raise _translate(exc) from exc
        except Exception as exc:
            raise _translate(exc) from exc

        try:
            return model.model_validate(raw)
        except ValidationError as exc:
            last_failure = exc
            if attempt + 1 < attempts:
                messages = _with_output_rule(messages)
                continue
            # The provider's own error is not shown. What is shown is that the
            # answer did not match the shape the application asked for, which
            # is a truthful description of what happened.
            logger.warning(
                "AI provider response failed validation against %s", model.__name__,
                extra={"kind": "ai"},
            )
            raise UnprocessableError(
                "The AI service returned an answer this application could not read. "
                "Please try again."
            ) from exc

    raise UnprocessableError(
        "The AI service returned an answer this application could not read. "
        "Please try again."
    ) from last_failure


def _with_output_rule(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """The prompt with the output-shape rule appended.

    The rule goes into the *existing* user message rather than a new one,
    because the model is given a single user message throughout and the
    provider's open-weight models do not take a system message.
    """
    from app.ml.prompts import STRUCTURED_OUTPUT_RULE

    if not messages:
        return messages
    first = dict(messages[0])
    first["content"] = f"{first.get('content', '')}\n\n{STRUCTURED_OUTPUT_RULE}"
    return [first, *messages[1:]]



def provider_status(settings: Settings | None = None) -> dict[str, Any]:
    """What the frontend is allowed to know about the provider.

    The model name and whether the feature is on. Never the key, never the
    base URL's credentials, never a request.
    """
    resolved = settings or get_settings()
    return {
        "enabled": resolved.groq_is_configured,
        "model": resolved.provider_model if resolved.groq_is_configured else "",
    }
