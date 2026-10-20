"""Sending mail.

The system has three transports, and the choice is made by configuration
rather than by code:

* **smtp** — a real mail server, used when ``SMTP_HOST`` is set. This is the
  production path.
* **file** — the message is written to a directory and the link is logged.
  This is the development path, and it exists so that the verification and
  password-reset flows can be exercised **end to end** without a mail
  provider, an account, or a network.
* **console** — the message is logged only. Useful in a container where
  writing files is not wanted.

The file transport is what makes the flows testable rather than merely
written. A flow that cannot be exercised is a flow that does not work.

Nothing here raises on a delivery failure. A user who cannot be sent a
verification email can still use the product, and a mail server outage must
not become a 500 on registration. The failure is logged, and the caller
carries on.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger("app.services.mail")

#: The transports, in the order they are considered.
TRANSPORTS = ("smtp", "file", "console")


def _selected_transport() -> str:
    settings = get_settings()
    if settings.smtp_host:
        return "smtp"
    if settings.mail_transport in ("file", "console"):
        return settings.mail_transport
    return "file"


def _build_message(to: str, subject: str, body: str) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
    message["To"] = to
    message.set_content(body)
    return message


def _smtp_context() -> ssl.SSLContext | None:
    """The SSL context for STARTTLS, or ``None`` when TLS is not in use.

    The context is built explicitly rather than left to ``smtplib``, which
    would otherwise use ``ssl.create_default_context()`` -- that verifies the
    server's certificate against the system trust store, which is right, but
    leaves no way to point at a private certificate authority and no way to
    turn verification off for a server with a self-signed certificate.

    Verification is on by default, and turning it off is a deliberate,
    named decision rather than a side effect.
    """
    settings = get_settings()
    if not settings.smtp_use_tls:
        return None
    if settings.smtp_tls_verify:
        if settings.smtp_ca_file:
            return ssl.create_default_context(cafile=settings.smtp_ca_file)
        return ssl.create_default_context()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _send_smtp(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = _build_message(to, subject, body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        context = _smtp_context()
        if context is not None:
            server.starttls(context=context)
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def _send_file(to: str, subject: str, body: str) -> Path:
    settings = get_settings()
    directory = Path(settings.mail_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{to.replace('@', '_at_')}.txt"
    path.write_text(
        f"To: {to}\nSubject: {subject}\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _send_console(to: str, subject: str, body: str) -> None:
    logger.info("Mail (console transport) to=%s subject=%s\n%s", to, subject, body)


def send(to: str, subject: str, body: str) -> str:
    """Send a message. Returns the transport that was used.

    Never raises: a mail failure is logged and swallowed, because a mail
    server outage must not turn a registration into a 500.
    """
    transport = _selected_transport()
    try:
        if transport == "smtp":
            _send_smtp(to, subject, body)
        elif transport == "console":
            _send_console(to, subject, body)
        else:
            path = _send_file(to, subject, body)
            logger.info("Mail written to %s (to=%s)", path, to)
    except Exception:
        logger.exception("Could not send mail to %s", to, extra={"kind": "mail"})
        return "failed"
    return transport


def send_verification_email(to: str, name: str, link: str) -> str:
    """The "confirm your address" message."""
    body = (
        f"Hello {name or 'there'},\n\n"
        "Please confirm your email address to finish setting up your CareerLens AI "
        "account.\n\n"
        f"{link}\n\n"
        "If you did not create an account, you can ignore this message — nothing will "
        "happen.\n"
    )
    return send(to, "Confirm your CareerLens AI account", body)


def send_password_reset_email(to: str, name: str, link: str) -> str:
    """The "reset your password" message."""
    body = (
        f"Hello {name or 'there'},\n\n"
        "Use the link below to choose a new password for your CareerLens AI account. "
        "It can be used once, and it expires shortly.\n\n"
        f"{link}\n\n"
        "If you did not ask for this, you can ignore this message — your password has "
        "not changed.\n"
    )
    return send(to, "Reset your CareerLens AI password", body)
