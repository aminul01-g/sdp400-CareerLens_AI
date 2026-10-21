"""``/api/ai`` — what the AI layer can and cannot do on this deployment.

One small endpoint, and it exists so the interface never has to guess. A
frontend that cannot tell whether the provider is configured will either hide
the AI features behind a spinner, or — worse — present a button that always
fails. This tells it the truth once.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.ai import AiStatusRead
from app.services import groq_service

router = APIRouter(prefix="/ai", tags=["ai"])

#: The features this deployment offers. Listed so the interface can show what
#: is available without hard-coding a list that could drift.
FEATURES = (
    "mentor",
    "roadmaps",
    "job-analysis",
    "cv-advice",
    "interview",
)


@router.get(
    "/status",
    response_model=AiStatusRead,
    summary="Whether the AI layer is available on this deployment",
)
def ai_status(user: CurrentUser) -> AiStatusRead:
    """The provider's availability, and which model is answering.

    Never the API key. The response is safe to show to a browser.
    """
    status = groq_service.provider_status()
    return AiStatusRead(
        enabled=bool(status["enabled"]),
        model=str(status["model"]),
        features=list(FEATURES) if status["enabled"] else [],
    )
