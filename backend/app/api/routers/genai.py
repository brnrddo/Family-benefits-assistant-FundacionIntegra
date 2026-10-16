"""Router ``genai``: askCatalogAssistant (FEAT-003; API-009).

El público envía solo una pregunta. Una consulta de elegibilidad individual se
detecta determinísticamente y devuelve ``REQUIRES_DETERMINISTIC_EVALUATION`` sin
invocar ningún proveedor LLM. En otro caso, información general del catálogo C4.
Una pregunta con RUT, teléfono o correo se rechaza con 422 sin ecoar el valor.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_scope
from app.api.errors import ApiError
from app.api.models import AssistantPublicRequest
from app.api.runtime import responder_asistente
from app.genai.template_provider import contiene_dato_personal

router = APIRouter(tags=["genai"])

_RAZON_DATO_PERSONAL = "La pregunta no debe incluir RUT, teléfono ni correo."


@router.post("/asistente")
def ask_catalog_assistant(
    request: Request,
    body: AssistantPublicRequest,
    _scope=Depends(require_scope("asistente:write")),
) -> dict:
    if contiene_dato_personal(body.question):
        raise ApiError(
            status_code=422,
            details=[{"field": "body.question", "reason": _RAZON_DATO_PERSONAL}],
            retryable=False,
        )
    return responder_asistente(body.question, request.state.request_id)
