"""Authentication request/response schemas.

``UserRead`` deliberately has no ``password_hash`` field. That is the whole point:
a response model that cannot express the hash cannot leak it. The legacy
Flask-Admin panel listed ``user.password_hash`` to anonymous visitors, which is
security finding S1 — hashes are offline-attackable.

The password policy (>= 8 characters, at least one uppercase, one lowercase, one
digit) is enforced here, on the server. The legacy ``backend/auth.py:14-15``
checked only that the field was present, so ``x`` was an acceptable password.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 120

_PASSWORD_COMPLEXITY = re.compile(
    r"""
    (?=.*[a-z])   # at least one lowercase letter
    (?=.*[A-Z])   # at least one uppercase letter
    (?=.*\d)      # at least one digit
    """,
    re.VERBOSE,
)


def validate_password_strength(value: str) -> str:
    """Raise a field error unless the password meets the policy."""
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters.")
    if not _PASSWORD_COMPLEXITY.search(value):
        raise ValueError(
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, and one digit."
        )
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=MAX_NAME_LENGTH)]
    email: EmailStr
    password: Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)]
    # Previously collected by the legacy register form and then silently dropped
    # on the floor at Register.tsx:92. It is now sent and stored.
    education_level: Annotated[str | None, Field(max_length=80)] = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be blank.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        # Security finding S9. Normalising here *and* relying on the functional
        # unique index on lower(email) means neither layer alone is load-bearing.
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)]

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class UserRead(BaseModel):
    """The only shape in which a user ever leaves the API.

    ``from_attributes`` lets it be built straight from the ORM object while still
    being an explicit allowlist, so adding a column to the model cannot leak it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    is_verified: bool = False
    created_at: Any = None


class TokenResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds.")


class RefreshRequest(BaseModel):
    """Refresh takes the current bearer token; the body is optional metadata."""


class UserUpdateRequest(BaseModel):
    """``PATCH /api/auth/me`` — name and/or password.

    Beyond the proposal's stated "Create, Read" for authentication, and recorded as
    an addition in the compliance matrix rather than a proposal requirement. A
    product with a delete button and no password change reads as obviously
    incomplete.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str | None, Field(min_length=1, max_length=MAX_NAME_LENGTH)] = None
    password: Annotated[
        str | None, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    ] = None
    current_password: Annotated[str | None, Field(max_length=MAX_PASSWORD_LENGTH)] = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Name must not be blank.")
        return value.strip() if value else value

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str | None) -> str | None:
        return validate_password_strength(value) if value is not None else None


class ForgotPasswordRequest(BaseModel):
    """``POST /api/auth/forgot-password``.

    The response is identical whether or not the address is registered, so
    this endpoint cannot be used to discover who has an account.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    """``POST /api/auth/reset-password``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    token: Annotated[str, Field(min_length=10, max_length=200)]
    new_password: Annotated[
        str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    ]

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_password_strength(value)


class VerifyEmailRequest(BaseModel):
    """``POST /api/auth/verify-email``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    token: Annotated[str, Field(min_length=10, max_length=200)]


class AcceptedResponse(BaseModel):
    """A 202: the request was accepted, and deliberately says nothing more.

    Used by the two endpoints that must not reveal whether an address exists.
    """

    status: str = "accepted"
    message: str
