"""Router de la propuesta ``addFamiliaAntecedentes`` (DEC-039/PREG-039).

``POST /familias/{id}/antecedentes``: la tía agrega antecedentes de una familia
EXISTENTE; cada campo se registra como hecho ``DECLARADO`` y la ficha se
reevalúa. Operación PROPUESTA por el Rol 3, implementada en servidor y FUERA de
C3 v1.0.2 (el contrato no se edita). Detalles y preguntas abiertas:
``backend/app/api/PROPUESTA_ANTECEDENTES.md``.

No llama IA. La elegibilidad la decide el motor determinista: aquí solo se
registran hechos y se pide reevaluación. La respuesta es el
``FamiliaDetailEnvelope`` de C3 sin cambios de forma, con el MISMO serializador
que ``GET /familias/{id}``.

Logs (API-013): solo ``request_id``, ruta normalizada, status y latencia. Nunca
el cuerpo, los valores declarados ni nombres de campo.
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, Header, Request

from app.api import antecedentes_store as store
from app.api import mock_data, motor_real
from app.api.antecedentes_service import aplicar_declarados, hechos_declarados
from app.api.deps import construir_meta, mock_habilitado, require_scope
from app.api.errors import ApiError
from app.api.models import InvarianteError
from app.api.models_antecedentes import AddFamilyInfoRequestV1
from app.api.serializers import familia_detail_data

logger = logging.getLogger("app.api.antecedentes")

router = APIRouter(tags=["familias"])

_RUTA_NORMALIZADA = "/familias/{id}/antecedentes"


@router.post("/familias/{id}/antecedentes", status_code=200)
def add_familia_antecedentes(
    request: Request,
    id: str,
    body: AddFamilyInfoRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _scope=Depends(require_scope("familias:write")),
) -> dict:
    """``operationId: addFamiliaAntecedentes``; scope ``familias:write``.

    200 éxito o repetición idempotente, 409 misma clave con otro cuerpo, 422
    cuerpo inválido o sin datos que declarar, 401 sin sesión, 503 motor no
    disponible. NUNCA 201: no crea un recurso visible.
    """
    inicio = time.perf_counter()
    try:
        respuesta = _procesar(request, id, body, idempotency_key)
    except ApiError as exc:
        _log(request, exc.status_code, inicio)
        raise
    _log(request, 200, inicio)
    return respuesta


def _log(request: Request, status: int, inicio: float) -> None:
    logger.info(
        "antecedentes rid=%s route=%s status=%s latency_ms=%.1f",
        getattr(request.state, "request_id", ""),
        _RUTA_NORMALIZADA,
        status,
        (time.perf_counter() - inicio) * 1000,
    )


def _reevaluar_con_motor(family_id: str, acumulados: list[dict]) -> dict | None:
    """Ficha C3 reevaluada por el motor real (B2), o ``None`` si no puede operar.

    Reconstruye el cuerpo declarado (campo de pantalla -> último valor conocido)
    desde los hechos acumulados y delega en ``motor_real``, que traduce lo que el
    motor sabe usar (hoy, la fecha del control de salud) y reevalúa la familia.
    Un valor "No sé" no fuerza un dato: se omite y el campo sigue indeterminado.
    """
    campos: dict = {}
    for hecho in acumulados:
        if hecho["desconocido"]:
            campos.pop(hecho["campo"], None)
        else:
            campos[hecho["campo"]] = hecho["valor"]
    familia = motor_real.reconstruir_familia_declarada(family_id, campos)
    if familia is None:
        return None
    try:
        return familia_detail_data(familia)
    except InvarianteError:
        return None


def _procesar(
    request: Request,
    id: str,
    body: AddFamilyInfoRequestV1,
    idempotency_key: str,
) -> dict:
    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        raise ApiError(status_code=422) from None

    if not motor_real.familia_existe(motor_real.obtener_snapshot(), id):
        # Se oculta la existencia igual que el resto de /familias/{id} (API-005).
        # Con el motor real activo se verifica contra los IDs reales (DEC-052).
        raise ApiError(status_code=404)

    declarados = body.model_dump(exclude_unset=True)
    declarados.pop("data_classification", None)
    if not declarados:
        # minProperties: 2 del schema del Rol 3: familia sin datos que declarar.
        raise ApiError(status_code=422)

    # El hash incluye la familia del path: la misma clave contra otro recurso es
    # un conflicto (409), nunca la ficha de la familia anterior.
    bhash = store.body_hash(id, body.model_dump(exclude_unset=True))
    cacheado = store.idem_get(idempotency_key)
    if cacheado is not None:
        prev_hash, data = cacheado
        if prev_hash != bhash:
            raise ApiError(status_code=409)
        # Repetición exacta: misma respuesta, sin efectos nuevos.
        return {"meta": construir_meta(request.state.request_id), "data": data}

    hechos = hechos_declarados(body)
    acumulados = store.declarados_get(id) + hechos

    if not mock_habilitado():
        # B2 · motor real: la fecha del último control de salud se convierte a
        # ``dias_desde_control`` del niño o niña más joven y se reevalúa la
        # familia con el motor determinista (R01203, versión vigente). El resto
        # de los campos no tiene mapeo al motor (ver antecedentes_motor.py): se
        # registran, pero no mueven elegibilidad por esta vía. Un dato declarado
        # nunca da CONFIRMADO. Si el motor no puede operar (sin DB/precálculo),
        # se falla cerrado y retryable (503).
        data = _reevaluar_con_motor(id, acumulados)
        if data is None:
            raise ApiError(status_code=503)
        store.declarados_add(id, hechos)
        store.idem_put(idempotency_key, bhash, data)
        return {"meta": construir_meta(request.state.request_id), "data": data}

    try:
        data = familia_detail_data(aplicar_declarados(mock_data.FAMILIAS[id], acumulados))
    except InvarianteError:
        # Reevaluación incoherente: se descarta por completo, nada se registra.
        raise ApiError(status_code=503) from None
    store.declarados_add(id, hechos)
    store.idem_put(idempotency_key, bhash, data)
    return {"meta": construir_meta(request.state.request_id), "data": data}
