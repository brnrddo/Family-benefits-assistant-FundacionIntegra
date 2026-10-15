"""Estado en memoria de la propuesta ``antecedentes`` (demo, por proceso).

Dos registros con el mismo criterio de demo que ``_IDEMPOTENCIA`` de
``routers/tracking.py``: viven en el proceso, no persisten entre reinicios y no
se comparten entre workers. Suficiente para la demo E-3; documentado como
limitación en ``PROPUESTA_ANTECEDENTES.md``.

No guardan nombres, identificadores civiles, contacto ni texto libre: solo el
ID seudónimo sintético de la familia y los campos cerrados declarados.
"""
from __future__ import annotations

import hashlib
import json

# idempotency_key -> (body_hash, data de FamilyDetail ya serializada)
_IDEMPOTENCIA: dict[str, tuple[str, dict]] = {}

# family_id -> hechos declarados acumulados (en orden de llegada)
_DECLARADOS: dict[str, list[dict]] = {}


def body_hash(payload: dict) -> str:
    """Hash canónico del cuerpo declarado.

    ``payload`` debe venir de ``model_dump(exclude_unset=True)``: sin eso,
    ``{"child_age": null}`` y ``{}`` colisionarían y la idempotencia no podría
    distinguir "No sé" de "sin cambio".
    """
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def idem_get(key: str) -> tuple[str, dict] | None:
    return _IDEMPOTENCIA.get(key)


def idem_put(key: str, bhash: str, data: dict) -> None:
    _IDEMPOTENCIA[key] = (bhash, data)


def declarados_get(family_id: str) -> list[dict]:
    return _DECLARADOS.get(family_id, [])


def declarados_add(family_id: str, hechos: list[dict]) -> None:
    _DECLARADOS.setdefault(family_id, []).extend(hechos)


def reset() -> None:
    """Vacía ambos registros (usado por los tests)."""
    _IDEMPOTENCIA.clear()
    _DECLARADOS.clear()
