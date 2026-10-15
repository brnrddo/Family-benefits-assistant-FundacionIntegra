"""Router ``jardines``: listJardines, listFamiliasByJardin (FEAT-003)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api import mock_data, motor_real
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.routers.tracking import familias_conversadas
from app.api.runtime import warnings_runtime

router = APIRouter(tags=["jardines"])


@router.get("/jardines")
def list_jardines(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    _scope=Depends(require_scope("jardines:read")),
) -> dict:
    snap = motor_real.obtener_snapshot()
    if snap is not None:
        # Jardines por garden_id; conteos de informadas desde las conversaciones.
        conversadas = familias_conversadas()
        todos = [motor_real.resumen_jardin(snap, g, conversadas) for g in snap.orden_jardines]
        items, siguiente = motor_real.paginar(snap, todos, limit, cursor)
        return {
            "meta": construir_meta(request.state.request_id),
            "items": items,
            "next_cursor": siguiente,
        }

    _ = warnings_runtime()
    items = mock_data.JARDINES[:limit]
    return {
        "meta": construir_meta(request.state.request_id),
        "items": items,
        "next_cursor": None,
    }


@router.get("/jardines/{id}/familias")
def list_familias_by_jardin(
    request: Request,
    id: str,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    _scope=Depends(require_scope("familias:read")),
) -> dict:
    snap = motor_real.obtener_snapshot()
    if snap is not None:
        if id not in snap.jardines:
            raise ApiError(status_code=404)
        # Orden estático del snapshot (prioridad sin conversación desc, ID asc):
        # marcar una conversación no reordena las páginas (DEC-051).
        conversadas = familias_conversadas()
        todas = [
            motor_real.resumen_familia(snap, f, f in conversadas)
            for f in snap.familias_por_jardin[id]
        ]
        items, siguiente = motor_real.paginar(snap, todas, limit, cursor)
        return {
            "meta": construir_meta(request.state.request_id),
            "items": items,
            "next_cursor": siguiente,
        }

    if not mock_data.jardin_existe(id):
        raise ApiError(status_code=404)
    items = mock_data.familias_de_jardin(id)[:limit]
    return {
        "meta": construir_meta(request.state.request_id),
        "items": items,
        "next_cursor": None,
    }
