"""Router ``genai``: askCatalogAssistant (FEAT-003; API-009).

El público envía solo una pregunta. Una consulta de elegibilidad individual se
detecta determinísticamente y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION`` sin
invocar ningún proveedor LLM. En otro caso, información general del catálogo C4.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_scope
from app.api.models import AssistantPublicRequest
from app.api.runtime import responder_asistente

router = APIRouter(tags=["genai"])


@router.post("/asistente")
def ask_catalog_assistant(
    request: Request,
    body: AssistantPublicRequest,
    _scope=Depends(require_scope("asistente:write")),
) -> dict:
    return responder_asistente(body.question, request.state.request_id)
