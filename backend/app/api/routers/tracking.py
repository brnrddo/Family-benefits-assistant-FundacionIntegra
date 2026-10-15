"""Router ``tracking``: createConversacion idempotente (FEAT-003; API-010).

Idempotencia de demo (en memoria, por proceso): misma ``Idempotency-Key`` +
mismo body devuelve el mismo registro; distinta key con body distinto crea otro;
misma key con body distinto -> 409.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response

from app.api import mock_data
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.models import ConversationRequest

router = APIRouter(tags=["tracking"])

# Registro idempotente de demo: idempotency_key -> (body_hash, record).
_IDEMPOTENCIA: dict[str, tuple[str, dict]] = {}


def _body_hash(body: ConversationRequest) -> str:
    payload = json.dumps(body.model_dump(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.post("/familias/{id}/conversaciones", status_code=201)
def create_conversacion(
    request: Request,
    response: Response,
    id: str,
    body: ConversationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _scope=Depends(require_scope("conversaciones:write")),
) -> dict:
    if not mock_data.familia_existe(id):
        raise ApiError(status_code=404)

    fam = mock_data.FAMILIAS[id]
    bhash = _body_hash(body)

    cacheado = _IDEMPOTENCIA.get(idempotency_key)
    if cacheado is not None:
        prev_hash, record = cacheado
        if prev_hash != bhash:
            # Misma clave, body distinto: conflicto de idempotencia.
            raise ApiError(status_code=409)
        return {"meta": construir_meta(request.state.request_id), "data": record}

    record = {
        "conversation_id": str(uuid.uuid4()),
        "family_id": id,
        "garden_id": fam["garden_id"],
        "benefit_ids": body.benefit_ids,
        "next_step": body.next_step,
        "channel": body.channel,
        "occurred_at": body.occurred_at,
        "snapshot_id": body.snapshot_id,
        "origin": body.origin,
        "status": "CONFIRMED",
    }
    _IDEMPOTENCIA[idempotency_key] = (bhash, record)
    return {"meta": construir_meta(request.state.request_id), "data": record}
