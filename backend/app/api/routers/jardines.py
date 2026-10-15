"""Router ``jardines``: listJardines, listFamiliasByJardin (FEAT-003)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api import mock_data
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.runtime import warnings_runtime

router = APIRouter(tags=["jardines"])


@router.get("/jardines")
def list_jardines(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2048),
    _scope=Depends(require_scope("jardines:read")),
) -> dict:
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
    if not mock_data.jardin_existe(id):
        raise ApiError(status_code=404)
    items = mock_data.familias_de_jardin(id)[:limit]
    return {
        "meta": construir_meta(request.state.request_id),
        "items": items,
        "next_cursor": None,
    }
