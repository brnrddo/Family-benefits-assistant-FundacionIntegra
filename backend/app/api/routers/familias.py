"""Router ``familias``: ficha, contexto, oportunidades, guion, mensaje, preevaluación.

Las operaciones de texto (guion/mensaje) viven con el tag ``genai`` en C3 pero
cuelgan de ``/familias/{id}``; se declaran aquí para mantener el prefijo. La
preevaluación se declara ANTES de ``/familias/{id}`` para que ``nueva`` no sea
capturado por el parámetro de ruta.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api import mock_data, motor_real
from app.api.antecedentes_service import aplicar_declarados
from app.api.antecedentes_store import declarados_get
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.models import FamilyGenerationPublicRequest, PreevaluationRequest
from app.api.routers.tracking import familias_conversadas
from app.api.runtime import generar_guion, generar_mensaje
from app.api.serializers import familia_detail_data
from app.priority.orden import ORDENES

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
    snap = motor_real.obtener_snapshot()
    if snap is not None:
        # Motor real (E3_MOCK=0): la ficha sale tal cual del precálculo del
        # Rol 1; solo ``informed`` depende de las conversaciones registradas.
        if id not in snap.familias:
            raise ApiError(status_code=404)
        vista = motor_real.vista_familia(snap, id, id in familias_conversadas())
        data = familia_detail_data(vista)
        return {"meta": construir_meta(request.state.request_id), "data": data}

    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    # Mismo serializador que la propuesta POST /antecedentes, y con los hechos
    # declarados aplicados para que la ficha reevaluada siga visible al refrescar.
    data = familia_detail_data(aplicar_declarados(fam, declarados_get(id)))
    return {"meta": construir_meta(request.state.request_id), "data": data}


@router.get("/familias/{id}/contexto")
def get_contexto_familia(
    request: Request,
    id: str,
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    snap = motor_real.obtener_snapshot()
    if snap is not None:
        # Vista minimizada y cerrada desde C2 por allowlist (DEC-049).
        if id not in snap.familias:
            raise ApiError(status_code=404)
        ctx = motor_real.contexto(snap, id)
        return {"meta": construir_meta(request.state.request_id), "data": ctx}

    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    ctx = aplicar_declarados(fam, declarados_get(id))["context"]
    return {"meta": construir_meta(request.state.request_id), "data": ctx}


@router.get("/familias/{id}/oportunidades")
def list_oportunidades(
    request: Request,
    id: str,
    orden: str = Query(default="prioridad"),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    snap = motor_real.obtener_snapshot()
    if snap is not None:
        if id not in snap.familias:
            raise ApiError(status_code=404)
        if orden not in ORDENES:
            raise ApiError(status_code=422)
        # Orden por grupo de acción (DEC-053) y paginación por cursor (DEC-051).
        items, siguiente = motor_real.paginar(
            snap, motor_real.oportunidades(snap, id, orden), limit, cursor
        )
        return {
            "meta": construir_meta(request.state.request_id),
            "items": items,
            "next_cursor": siguiente,
        }

    fam = mock_data.FAMILIAS.get(id)
    if fam is None:
        raise ApiError(status_code=404)
    if orden not in ("prioridad", "urgencia", "beneficio"):
        raise ApiError(status_code=422)
    # Coherencia con la ficha: misma reevaluación por hechos declarados.
    items = aplicar_declarados(fam, declarados_get(id))["opportunities"][:limit]
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
    if not motor_real.familia_existe(motor_real.obtener_snapshot(), id):
        raise ApiError(status_code=404)
    return generar_guion(body.benefit_ids, request.state.request_id)


@router.post("/familias/{id}/mensaje", tags=["genai"])
def create_mensaje(
    request: Request,
    id: str,
    body: FamilyGenerationPublicRequest,
    _scope=Depends(require_scope("genai:write")),
) -> dict:
    if not motor_real.familia_existe(motor_real.obtener_snapshot(), id):
        raise ApiError(status_code=404)
    return generar_mensaje(body.benefit_ids, request.state.request_id)
