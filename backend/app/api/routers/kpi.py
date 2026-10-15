"""Router ``kpi``: getKpi (FEAT-003; API-011)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api import mock_data
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError

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
    data = mock_data.kpi_sintetico(nivel, id, desde, hasta)
    return {"meta": construir_meta(request.state.request_id), "data": data}
