"""Router ``kpi``: getKpi (FEAT-003; API-011).

Con ``E3_MOCK=0`` y el snapshot del motor disponible, el KPI sale del registro
real de conversaciones sobre las familias del snapshot (B3, ``kpi_real``); si
no, se sirve el mock sintético de siempre.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api import kpi_real, mock_data, motor_real
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.routers import tracking

router = APIRouter(tags=["kpi"])

_NIVELES = {"jardin", "comuna", "region", "nacional"}


@router.get("/kpi")
def get_kpi(
    request: Request,
    nivel: str = Query(...),
    id: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    _scope=Depends(require_scope("kpi:read")),
) -> dict:
    if nivel not in _NIVELES:
        raise ApiError(status_code=422)
    snap = motor_real.obtener_snapshot()
    if snap is None:
        data = mock_data.kpi_sintetico(nivel, id, desde, hasta)
        return {"meta": construir_meta(request.state.request_id), "data": data}
    data = kpi_real.calcular(snap, tracking.conversaciones(), nivel, id, desde, hasta)
    meta = construir_meta(request.state.request_id, contenido=motor_real.procedencia(snap))
    return {"meta": meta, "data": data}
