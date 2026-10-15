"""Router ``catalogo``: ingestSyntheticFlyer (FEAT-003; API-017).

Acepta SOLO ``TextractFlyerRequestV1`` (metadata de un asset sintético
inventariado). Rechaza bytes/base64/URL/clave S3 u otros campos extra con 422.
El resultado SIEMPRE queda ``PENDIENTE_REVISION`` (revisión humana).
"""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api import mock_data
from app.api.deps import construir_meta, require_scope

router = APIRouter(tags=["catalogo"])

_ASSET_PATTERN = r"^[A-Z0-9][A-Z0-9_-]*$"


class TextractFlyerRequest(BaseModel):
    """Espejo cerrado de TextractFlyerRequestV1.schema.json (additionalProperties:false)."""

    model_config = ConfigDict(extra="forbid")

    synthetic_asset_id: str = Field(min_length=1, max_length=80, pattern=_ASSET_PATTERN)
    media_type: Literal["image/jpeg", "image/png"]
    sha256: str

    @field_validator("sha256")
    @classmethod
    def _sha_valido(cls, v: str) -> str:
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError("sha256 debe ser 64 hex en minúscula")
        return v


@router.post("/catalogo/ingesta-afiche")
def ingest_synthetic_flyer(
    request: Request,
    body: TextractFlyerRequest,
    _scope=Depends(require_scope("catalogo:admin")),
) -> dict:
    data = mock_data.flyer_draft(body.synthetic_asset_id)
    return {"meta": construir_meta(request.state.request_id), "data": data}
