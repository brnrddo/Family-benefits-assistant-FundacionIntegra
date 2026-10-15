"""Router ``tracking``: createConversacion idempotente (FEAT-003; API-010).

Idempotencia de demo (en memoria, por proceso): misma ``Idempotency-Key`` +
mismo body devuelve el mismo registro; distinta key con body distinto crea otro;
misma key con body distinto -> 409.
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response

from app.api import motor_real
from app.api.deps import construir_meta, require_scope
from app.api.errors import ApiError
from app.api.models import ConversationRequest

router = APIRouter(tags=["tracking"])

# Registro idempotente de demo: idempotency_key -> (body_hash, record).
_IDEMPOTENCIA: dict[str, tuple[str, dict]] = {}
# Las rutas síncronas corren en el threadpool: lectura y escritura del registro
# van bajo el mismo lock (un GET no puede recorrerlo mientras un POST inserta).
_LOCK_IDEMPOTENCIA = threading.Lock()


def familias_conversadas() -> frozenset[str]:
    """``family_id`` con al menos una conversación registrada en este proceso.

    Alimenta ``informed``/``conversation_status`` y los conteos de jardín del
    motor real (decisión 10). No cambia el registro idempotente.
    """
    with _LOCK_IDEMPOTENCIA:
        registros = list(_IDEMPOTENCIA.values())
    return frozenset(record["family_id"] for _, record in registros)


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
    # Existencia y jardín desde UN mismo snapshot (motor real si está activo; si
    # no, el mock): si la DB cambia entre medio, nunca se mezclan fuentes.
    snap = motor_real.obtener_snapshot()
    garden_id = motor_real.garden_de(snap, id)
    if garden_id is None:
        raise ApiError(status_code=404)
    # Con el motor real, meta declara el bundle content/ del snapshot (DEC-062).
    meta = construir_meta(request.state.request_id, contenido=motor_real.procedencia(snap))

    bhash = _body_hash(body)

    with _LOCK_IDEMPOTENCIA:
        cacheado = _IDEMPOTENCIA.get(idempotency_key)
        if cacheado is not None:
            prev_hash, record = cacheado
            if prev_hash != bhash:
                # Misma clave, body distinto: conflicto de idempotencia.
                raise ApiError(status_code=409)
            return {"meta": meta, "data": record}

        record = {
            "conversation_id": str(uuid.uuid4()),
            "family_id": id,
            "garden_id": garden_id,
            "benefit_ids": body.benefit_ids,
            "next_step": body.next_step,
            "channel": body.channel,
            "occurred_at": body.occurred_at,
            "snapshot_id": body.snapshot_id,
            "origin": body.origin,
            "status": "CONFIRMED",
        }
        _IDEMPOTENCIA[idempotency_key] = (bhash, record)
    return {"meta": meta, "data": record}
