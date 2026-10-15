"""Router ``familias``: ficha, contexto, oportunidades, guion, mensaje, preevaluación.

Las operaciones de texto (guion/mensaje) viven con el tag ``genai`` en C3 pero
cuelgan de ``/familias/{id}``; se declaran aquí para mantener el prefijo. La
preevaluación se declara ANTES de ``/familias/{id}`` para que ``nueva`` no sea
capturado por el parámetro de ruta.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api import mock_data
from app.api.deps import DISCLAIMER, construir_meta, require_scope
from app.api.errors import ApiError
from app.api.models import FamilyGenerationPublicRequest, PreevaluationRequest
from app.api.runtime import generar_guion, generar_mensaje

router = APIRouter(tags=["familias"])


# --- Preevaluación: declarada ANTES de /familias/{id} ------------------------


@router.post("/familias/nueva/preevaluacion")
def create_preevaluacion(
    request: Request,
    body: PreevaluationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _scope=Depends(require_scope("familias:write")),
) -> dict:
    # Siempre PRELIMINAR; sin lógica de ingreso mínimo ni gate (fuera de alcance).
    data = mock_data.preevaluacion_resultado("FAM-SIM-PREEVAL")
    return {"meta": construir_meta(request.state.request_id), "data": data}


# --- Ficha, contexto, oportunidades ------------------------------------------


@router.get("/familias/{id}")
def get_familia(
    request: Request,
    id: str,
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    data = {
        "family_id": fam["summary"]["family_id"],
        "garden_id": fam["garden_id"],
        "composition": fam["composition"],
        "rsh_band": fam["rsh_band"],
        "informed": fam["informed"],
        "top_opportunities": fam["opportunities"][:3],
        "benefit_results": fam["benefit_results"],
        "disclaimer": DISCLAIMER,
    }
    return {"meta": construir_meta(request.state.request_id), "data": data}


@router.get("/familias/{id}/contexto")
def get_contexto_familia(
    request: Request,
    id: str,
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    return {"meta": construir_meta(request.state.request_id), "data": fam["context"]}


@router.get("/familias/{id}/oportunidades")
def list_oportunidades(
    request: Request,
    id: str,
    orden: str = Query(default="prioridad"),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    if orden not in ("prioridad", "urgencia", "beneficio"):
        raise ApiError(status_code=422)
    items = fam["opportunities"][:limit]
    return {
        "meta": construir_meta(request.state.request_id),
        "items": items,
        "next_cursor": None,
    }


# --- Generación de texto (tag genai, bajo /familias/{id}) --------------------


@router.post("/familias/{id}/guion", tags=["genai"])
def create_guion(
    request: Request,
    id: str,
    body: FamilyGenerationPublicRequest,
    _scope=Depends(require_scope("genai:write")),
) -> dict:
    if not mock_data.familia_existe(id):
        raise ApiError(status_code=404)
    return generar_guion(body.benefit_ids, request.state.request_id)


@router.post("/familias/{id}/mensaje", tags=["genai"])
def create_mensaje(
    request: Request,
    id: str,
    body: FamilyGenerationPublicRequest,
    _scope=Depends(require_scope("genai:write")),
) -> dict:
    if not mock_data.familia_existe(id):
        raise ApiError(status_code=404)
    return generar_mensaje(body.benefit_ids, request.state.request_id)
