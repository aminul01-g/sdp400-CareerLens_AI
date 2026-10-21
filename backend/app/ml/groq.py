"""The Groq provider client. One HTTP call site for the whole AI layer.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
Pure module                    Imports only the standard library, so it
                               inherits the ML layer's
                               no-ORM / no-web-framework guarantee and adds
                               no runtime dependency. It cannot read
                               configuration, so credentials arrive as plain
                               arguments
No credential in a log          Nothing here logs a request, a response or a
                               header. The failure messages carry the status
                               code and the provider's *error type*, never the
                               body, which for a 401 would otherwise contain
                               the key that was rejected
Bounded retries                ``max_retries`` is a hard ceiling and defaults
                               to one extra attempt. An unbounded retry loop
                               against a metered API is a denial of wallet
============================  ==========================================

The model family matters here. Groq's open-weight reasoning models
(``openai/gpt-oss-*``) do not support a ``system`` message — Groq's own
guidance is to put every instruction in the user message — and they expose
``reasoning_effort`` and ``include_reasoning``, which other models do not.
Sending either to a model that does not understand it is a 400, so both are
emitted only for the families that document them.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("app.ml.groq")

#: How long to wait before the next attempt. Long enough for a provider blip
#: to pass, short enough that a user does not stare at a spinner.
RETRY_BACKOFF_SECONDS = 0.4

#: The ceiling on a single response. The roadmaps and job analyses are the
#: longest outputs; 6 000 tokens is comfortably above what they need and
#: well below the model's own limit.
DEFAULT_MAX_COMPLETION_TOKENS = 6000

#: Model id prefixes whose provider accepts the reasoning controls.
_REASONING_MODEL_PREFIXES = ("openai/gpt-oss-", "qwen/", "meta-models/muse-spark-")

#: The ``User-Agent`` sent with every request.
#:
#: The provider sits behind an edge that rejects the standard library's
#: default agent -- ``Python-urllib/3.12`` -- with ``403`` and
#: ``error code: 1010``, which is the edge's "your signature is banned"
#: response. A request that is otherwise perfectly valid therefore fails, and
#: it fails in a way that looks like a credential problem rather than a header
#: problem.
#:
#: This was found by calling the real provider, not by reading about it, and it
#: is the kind of defect a mocked test suite cannot see. The agent below
#: identifies the application, which is what the edge wants to see.
USER_AGENT = "careerlens-ai/1.0 (+https://github.com/aminul01-g/sdp400-CareerLens_AI)"

#: The model family used when nothing else is configured.
DEFAULT_MODEL = "openai/gpt-oss-120b"


class GroqError(Exception):
    """Base class for every provider failure.

    The message is written for a server log, not for a client. ``app.services``
    maps these onto the application's own error types, and the provider's raw
    text never reaches the user.
    """


class GroqConfigError(GroqError):
    """The provider was asked to do work without the configuration to do it."""


class GroqAuthenticationError(GroqError):
    """The provider rejected the API key."""


class GroqRateLimitedError(GroqError):
    """The provider is rate limiting us."""


class GroqInvalidRequestError(GroqError):
    """The provider rejected the request — a bad schema, or an unknown model."""


class GroqServerError(GroqError):
    """The provider failed on its side."""


class GroqTimeoutError(GroqError):
    """The provider did not answer in time."""


class GroqUnavailableError(GroqError):
    """The provider could not be reached at all."""


class GroqInvalidResponseError(GroqError):
    """The provider answered, but not with something we can use."""


def _supports_reasoning_controls(model: str) -> bool:
    """Whether ``model`` accepts ``reasoning_effort`` / ``include_reasoning``.

    Sending a parameter a model does not know is a 400 from Groq, and a 400
    for a *reasoning* request is indistinguishable from a 400 for a bad
    schema when the provider's message is not surfaced. So the parameters are
    emitted only for the families that document them.
    """
    lowered = model.strip().lower()
    return lowered.startswith(_REASONING_MODEL_PREFIXES)


def _provider_error_code(body: bytes) -> str:
    """The provider's machine-readable error code, if it sent one.

    Only the *code* is read, never the message. The message of a schema
    failure contains the generated output, and the generated output can echo
    the user's CV or job description. The code — ``json_validate_failed``,
    ``model_decommissioned`` — is what makes the failure diagnosable without
    putting the document in the log.
    """
    try:
        parsed = json.loads(body.decode("utf-8", errors="ignore"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ""
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return ""


def _error_for_status(status_code: int, error_code: str = "") -> GroqError:
    """Map a provider status code onto a typed error.

    The provider's body is deliberately not included. It can echo the request,
    and the request carries the user's document. The machine-readable code is
    safe, because it says what went wrong without saying what was sent.
    """
    suffix = f", {error_code}" if error_code else ""
    if status_code in (401, 403):
        return GroqAuthenticationError(
            f"provider rejected the credential ({status_code}{suffix})"
        )
    if status_code == 429:
        return GroqRateLimitedError("provider rate limited the request (429)")
    if status_code == 400:
        return GroqInvalidRequestError(
            f"provider rejected the request as invalid (400{suffix})"
        )
    if status_code == 404:
        return GroqInvalidRequestError(
            f"provider does not know that model or endpoint (404{suffix})"
        )
    return GroqServerError(f"provider failed ({status_code}{suffix})")


def _extract_content(body: dict[str, Any]) -> str:
    """Pull the assistant's text out of a chat-completion body.

    A reasoning model may return its thinking in a separate ``reasoning``
    field. That is not the answer, so only ``content`` is read.
    """
    try:
        choices = body["choices"]
    except (KeyError, TypeError) as exc:
        raise GroqInvalidResponseError("provider response had no choices") from exc
    if not isinstance(choices, list) or not choices:
        raise GroqInvalidResponseError("provider response had no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise GroqInvalidResponseError("provider response choice was not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise GroqInvalidResponseError("provider response had no message")
    content = message.get("content")
    if content is None:
        # An empty completion is a legitimate outcome for a refused prompt, and
        # it is the caller's job to decide what to do about it.
        return ""
    if not isinstance(content, str):
        raise GroqInvalidResponseError("provider response content was not text")
    return content


def _is_retryable(error: Exception) -> bool:
    """Whether another attempt could plausibly succeed.

    Rate limits, provider-side failures, timeouts and transport errors are
    worth retrying -- except a **rate limit**, which is not. The provider's
    quota is per *organisation*, not per request, so another attempt a
    fraction of a second later is rejected for the same reason. Retrying it
    burns the allowance and delays the 429 the caller should have been told
    about straight away, so a rate limit is surfaced instead.
    """
    if isinstance(error, GroqRateLimitedError):
        return False
    return isinstance(
        error,
        (GroqServerError, GroqTimeoutError, GroqUnavailableError),
    )


def _post(
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    """One HTTPS POST. Returns the parsed body.

    The provider's response body is read but never logged and never returned
    to a client; it is parsed here and reduced to the assistant's text.
    """
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        # The body may echo the request, and it may echo the generated
        # output. Only the machine-readable error code is kept.
        try:
            raw_error = exc.read()
        except Exception:  # pragma: no cover - defensive
            raw_error = b""
        raise _error_for_status(exc.code, _provider_error_code(raw_error)) from exc
    except TimeoutError as exc:
        # ``socket.timeout`` is an alias of ``TimeoutError`` since Python 3.10,
        # so this covers both a read that took too long and a connect that
        # took too long.
        raise GroqTimeoutError(f"provider did not answer within {timeout}s") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise GroqTimeoutError(f"provider did not answer within {timeout}s") from exc
        raise GroqUnavailableError("provider could not be reached") from exc
    except OSError as exc:
        raise GroqUnavailableError("provider could not be reached") from exc

    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GroqInvalidResponseError("provider returned a body that is not JSON") from exc
    if not isinstance(body, dict):
        raise GroqInvalidResponseError("provider response was not a JSON object")
    return body


def complete(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    base_url: str = "https://api.groq.com/openai/v1",
    timeout: int = 45,
    max_retries: int = 1,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "response",
    strict: bool = True,
    temperature: float = 0.4,
    reasoning_effort: str | None = None,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    backoff_seconds: float = RETRY_BACKOFF_SECONDS,
) -> str:
    """One chat completion. Returns the assistant's text.

    With ``json_schema`` the provider is asked for a schema-constrained
    response, and with ``strict`` it is asked to *guarantee* the shape by
    constraining decoding rather than by hoping. The guarantee is on the
    provider's side; this function still hands the raw text back, and
    :mod:`app.services.groq_service` validates it against the Pydantic model
    before anything is shown to a user or written to the database.

    Raises a :class:`GroqError` subclass on every failure. It never returns a
    partial answer.
    """
    if not api_key.strip():
        raise GroqConfigError("no API key was supplied for the AI provider")
    if not messages:
        raise GroqConfigError("no messages were supplied for the AI provider")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
    }

    if json_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": strict,
                "schema": json_schema,
            },
        }

    if _supports_reasoning_controls(model):
        # Keep the reasoning out of the answer. The user asked a career
        # question, not for a transcript of the model's deliberation, and the
        # thinking is not something to store or display.
        payload["include_reasoning"] = False
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    attempts = max(0, int(max_retries)) + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            body = _post(endpoint, payload, headers, timeout)
        except GroqError as exc:
            last_error = exc
            logger.warning(
                "AI provider call failed on attempt %s: %s",
                attempt + 1,
                type(exc).__name__,
                extra={"kind": "ai"},
            )
        else:
            return _extract_content(body)

        if attempt + 1 >= attempts or not _is_retryable(last_error):
            break
        if backoff_seconds > 0:
            time.sleep(backoff_seconds)

    assert last_error is not None
    raise last_error


def complete_json(
    messages: list[dict[str, str]],
    *,
    json_schema: dict[str, Any],
    schema_name: str = "response",
    **kwargs: Any,
) -> dict[str, Any]:
    """A completion constrained to ``json_schema``, returned as a dictionary.

    The parse is strict on purpose. A provider that answers with prose around
    the JSON is a provider whose output cannot be trusted to fill a database
    column, and the caller is better served by a clean error than by a
    half-parsed document.

    One accommodation is made, because it was observed against the real
    provider rather than imagined: a schema-constrained response occasionally
    arrives as a **single-element array wrapping the object**. The
    constrained decoder is not always applied to the outermost container, and
    the model then puts the object in a list. Unwrapping a list of exactly one
    object is unambiguous — there is no reading of a one-element list of
    objects that means anything else — so it is unwrapped, and anything else
    is still refused.
    """
    raw = complete(
        messages,
        json_schema=json_schema,
        schema_name=schema_name,
        **kwargs,
    )
    text = raw.strip()
    if not text:
        raise GroqInvalidResponseError("provider returned an empty response")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GroqInvalidResponseError("provider response was not valid JSON") from exc
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise GroqInvalidResponseError("provider response was not a JSON object")
    return parsed
