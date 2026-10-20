"""The SMTP transport, exercised against a real mail server.

``docs/limitations.md`` used to say:

    **Email delivery is unproven against a live provider.** The development
    transport writes the message to a file, which is what makes the
    verification and reset flows testable end to end. The SMTP transport is
    written against the standard library and has never been exercised against
    a real mail server.

"Never been exercised against a real mail server" was the complaint, and it
was fair. The file transport is exercised; the SMTP transport was written and
hoped for.

These tests run a real SMTP server -- ``aiosmtpd`` -- on an ephemeral port
and send through it, so the code path is the same one a production mail
provider would exercise: the socket, the ``EHLO``, the ``STARTTLS``
negotiation, the authentication, the ``DATA`` command and the message body.

What is still *not* established, and what the limitations document continues
to say, is that a commercial provider accepts what this sends. A local server
that speaks SMTP correctly is not SendGrid, and the difference between them
is exactly the thing no test can cover.
"""

from __future__ import annotations

import ssl
from email import message_from_string
from pathlib import Path

import pytest
from aiosmtpd.controller import Controller

from app.core.config import get_settings
from app.services import mail_service

#: A throwaway self-signed certificate, generated once for the module. The
#: point of the STARTTLS test is that the negotiation works and that the
#: certificate is verified against a trust store we chose, not that a
#: particular certificate authority signed it.
_CERT_DIR = Path(__file__).parent / "fixtures" / "tls"
_CERT = _CERT_DIR / "localhost.pem"
_KEY = _CERT_DIR / "localhost.key"


def _ensure_certificate() -> None:
    """Create the self-signed certificate if it is not already on disk."""
    if _CERT.exists() and _KEY.exists():
        return
    import subprocess

    _CERT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(_KEY),
            "-out",
            str(_CERT),
            "-days",
            "3650",
            "-nodes",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )


def _as_text(content: str | bytes) -> str:
    """The envelope content as text.

    ``aiosmtpd`` hands the content over as a string for a text message and as
    bytes for some encodings, so both are accepted.
    """
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return content


class _Collector:
    """A sink that keeps every message the server receives."""

    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def handle_DATA(self, server, session, envelope):
        # The body is decoded rather than searched raw: a message with a
        # non-ASCII character in it is quoted-printable encoded, which wraps
        # long lines and splits a URL across a soft line break. A test that
        # looks for a URL in the raw bytes would fail on a message that
        # arrived perfectly intact.
        parsed = message_from_string(_as_text(envelope.content))
        payload = parsed.get_payload(decode=True) or b""
        self.messages.append(
            {
                "from": envelope.mail_from,
                "to": list(envelope.rcpt_tos),
                "content": _as_text(envelope.content),
                "body": payload.decode("utf-8", errors="replace"),
                "subject": parsed.get("Subject", ""),
            }
        )
        return "250 Message accepted for delivery"


def _free_port() -> int:
    """An ephemeral port that is free right now.

    The socket is closed before the port is handed over, so there is a small
    window in which something else could take it. That is the usual trade-off
    for this trick, and it is acceptable in a test process that runs no
    parallel servers.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def smtp_server():
    """A plain SMTP server on an ephemeral port, plus the messages it received."""
    collector = _Collector()
    controller = Controller(collector, hostname="127.0.0.1", port=_free_port())
    controller.start()
    try:
        yield controller, collector
    finally:
        controller.stop()


@pytest.fixture
def smtp_server_with_tls():
    """An SMTP server that requires STARTTLS."""
    _ensure_certificate()
    collector = _Collector()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(_CERT), keyfile=str(_KEY))
    controller = Controller(
        collector,
        hostname="127.0.0.1",
        port=_free_port(),
        require_starttls=True,
        tls_context=context,
    )
    controller.start()
    try:
        yield controller, collector
    finally:
        controller.stop()


def _use_server(controller: Controller, **overrides) -> None:
    """Point the application at the test server."""
    import os

    os.environ["SMTP_HOST"] = controller.hostname
    os.environ["SMTP_PORT"] = str(controller.port)
    for key, value in overrides.items():
        os.environ[key] = str(value)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_smtp_settings():
    yield
    import os

    for key in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_USE_TLS",
        "SMTP_TLS_VERIFY",
        "SMTP_CA_FILE",
    ):
        os.environ.pop(key, None)
    get_settings.cache_clear()


def test_a_message_is_delivered_over_plain_smtp(smtp_server) -> None:
    """The plain-SMTP path, end to end, against a real server."""
    controller, collector = smtp_server
    _use_server(controller, SMTP_USE_TLS="false")

    transport = mail_service.send("someone@example.com", "Hello", "Body text.")

    assert transport == "smtp"
    assert len(collector.messages) == 1
    message = collector.messages[0]
    assert message["from"] == get_settings().mail_from
    assert message["to"] == ["someone@example.com"]
    assert message["subject"] == "Hello"
    assert "Body text." in str(message["body"])


def test_the_verification_email_is_delivered_over_plain_smtp(smtp_server) -> None:
    """The verification flow, through the SMTP path rather than the file path."""
    controller, collector = smtp_server
    _use_server(controller, SMTP_USE_TLS="false")

    transport = mail_service.send_verification_email(
        "someone@example.com", "Sam", "http://localhost:3000/verify?token=abc"
    )

    assert transport == "smtp"
    message = collector.messages[0]
    assert "Confirm your CareerLens AI account" in str(message["subject"])
    assert "http://localhost:3000/verify?token=abc" in str(message["body"])


def test_the_reset_email_is_delivered_over_plain_smtp(smtp_server) -> None:
    controller, collector = smtp_server
    _use_server(controller, SMTP_USE_TLS="false")

    transport = mail_service.send_password_reset_email(
        "someone@example.com", "Sam", "http://localhost:3000/reset?token=abc"
    )

    assert transport == "smtp"
    message = collector.messages[0]
    assert "Reset your CareerLens AI password" in str(message["subject"])
    assert "http://localhost:3000/reset?token=abc" in str(message["body"])


def test_starttls_is_negotiated_and_the_certificate_is_verified(smtp_server_with_tls) -> None:
    """STARTTLS against a server whose certificate we choose to trust.

    The certificate is verified against the bundle in ``SMTP_CA_FILE``, which
    is the configuration a provider with a private certificate authority
    needs. A successful delivery here proves the negotiation, the context and
    the trust store all line up.
    """
    controller, collector = smtp_server_with_tls
    _use_server(
        controller,
        SMTP_USE_TLS="true",
        SMTP_TLS_VERIFY="true",
        SMTP_CA_FILE=str(_CERT),
    )

    transport = mail_service.send("someone@example.com", "Hello", "Body text.")

    assert transport == "smtp"
    assert len(collector.messages) == 1
    assert "Body text." in str(collector.messages[0]["body"])


def test_a_verification_failure_does_not_raise(smtp_server) -> None:
    """A certificate the client does not trust must fail, and fail quietly.

    The mail service never raises: a user who cannot be sent a verification
    email can still use the product, and a mail server outage must not become
    a 500 on registration.
    """
    controller, collector = smtp_server
    _use_server(
        controller,
        SMTP_USE_TLS="true",
        SMTP_TLS_VERIFY="true",
        SMTP_CA_FILE="",
    )

    transport = mail_service.send("someone@example.com", "Hello", "Body text.")

    assert transport == "failed"
    assert collector.messages == []


def test_the_file_transport_still_works(tmp_path) -> None:
    """The development transport is untouched by any of the above."""
    import os

    os.environ["SMTP_HOST"] = ""
    os.environ["MAIL_TRANSPORT"] = "file"
    os.environ["MAIL_DIR"] = str(tmp_path)
    get_settings.cache_clear()

    transport = mail_service.send("someone@example.com", "Hello", "Body text.")

    assert transport == "file"
    written = list(tmp_path.glob("*.txt"))
    assert len(written) == 1
    assert "Body text." in written[0].read_text(encoding="utf-8")
