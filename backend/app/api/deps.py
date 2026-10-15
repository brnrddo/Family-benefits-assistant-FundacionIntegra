"""Configuración y dependencias de la API (FEAT-003).

Reúne la configuración por entorno (bandera ``E3_MOCK``), las constantes de
demo (snapshot/hashes/versión), el constructor de ``EnvelopeMetadata`` con
``request_id`` por request y un stub de autorización por scope.

Principios (API-004/API-005/API-013, PRIVACIDAD_DEMO):

- Cognito real es ``NO_VERIFICADO``: aquí solo hay un stub de scope por header
  de demo para que Rol 3 pueda ejercitar 401/403/404 sin AWS.
- Fuera de scope se oculta la existencia del recurso con 404 (nunca 403 que
  confirme que el recurso existe).
- Nada que viaje aquí contiene PII ni secretos.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from fastapi import Header, Request

from app.api.errors import ApiError

# --- Config por entorno ------------------------------------------------------


def _env_bool(nombre: str, default: bool) -> bool:
    """Lee una bandera booleana desde entorno (mismo criterio que app.config)."""
    val = os.environ.get(nombre)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "si", "sí")


def mock_habilitado() -> bool:
    """``E3_MOCK`` (default True): todo responde con mocks sintéticos.

    Se lee en cada request (no se cachea en import) para que los tests puedan
    alternar la bandera con ``monkeypatch.setenv`` sin recargar módulos.
    """
    return _env_bool("E3_MOCK", True)


# --- Constantes de demo (deterministas, sin PII) -----------------------------

# snapshot_id respeta el patrón Id de C3: ^[A-Z0-9][A-Z0-9_-]*$
SNAPSHOT_ID = "SNAP-DEMO-0001"

# Hashes de 64 hex CONSTANTES (placeholders de demo; no identifican datos reales).
ELIGIBILITY_BUNDLE_HASH = "1" * 64
CONTENT_BUNDLE_HASH = "0" * 64

# Versión de contenido (coincide con el bundle C4 provisional).
CONTENT_VERSION = "0.1.0"

# Aviso referencial exacto exigido por C3 (con tildes). No modificar.
DISCLAIMER = "Orientación referencial; no determina derechos. Confirmar en la institución."


def nuevo_request_id() -> str:
    """request_id corto y seguro (sin PII), ≤80 chars."""
    return f"REQ-{uuid.uuid4().hex}"


def construir_meta(request_id: str | None = None) -> dict:
    """Construye el ``EnvelopeMetadata`` cerrado de C3."""
    return {
        "request_id": request_id or nuevo_request_id(),
        "snapshot_id": SNAPSHOT_ID,
        "eligibility_bundle_hash": ELIGIBILITY_BUNDLE_HASH,
        "content_bundle_hash": CONTENT_BUNDLE_HASH,
        "content_version": CONTENT_VERSION,
    }


# --- Stub de autorización por scope ------------------------------------------
#
# Cognito real queda NO_VERIFICADO (ARQUITECTURA_AWS). En demo, un header
# opcional declara el scope del cliente. Si NO se envía ningún header de scope,
# se considera un cliente de demo con todos los scopes (para no romper al Rol 3
# ni a /docs). Si se envía el header, se exige que incluya el scope requerido:
# ausencia de credencial declarada => 401; scope insuficiente => se oculta con
# 404 (API-005) salvo en operaciones de escritura puras sin recurso, donde 403.

_SCOPE_HEADER = "x-demo-scopes"


@dataclass(frozen=True)
class ScopeContext:
    """Scopes declarados por el cliente de demo."""

    scopes: frozenset[str]
    declarado: bool  # True si el cliente envió el header de scope


def _parse_scopes(valor: str | None) -> ScopeContext:
    if valor is None:
        # Sin credencial declarada: demo abierta con todos los scopes.
        return ScopeContext(scopes=frozenset(), declarado=False)
    partes = {s.strip() for s in valor.split(",") if s.strip()}
    return ScopeContext(scopes=frozenset(partes), declarado=True)


def require_scope(scope: str):
    """Devuelve una dependencia FastAPI que exige ``scope`` (stub de demo).

    - Sin header declarado -> permitido (demo abierta).
    - Header declarado sin el scope -> 404 (ocultar existencia), API-005.
    - Header declarado vacío -> 401 (credencial presente pero sin scopes).
    """

    def _dep(
        request: Request,
        x_demo_scopes: str | None = Header(default=None, alias=_SCOPE_HEADER),
    ) -> ScopeContext:
        ctx = _parse_scopes(x_demo_scopes)
        if not ctx.declarado:
            return ctx
        if not ctx.scopes:
            raise ApiError(
                status_code=401,
                code="UNAUTHENTICATED",
                message="Credencial de demo sin scopes.",
            )
        if scope not in ctx.scopes:
            # Ocultar existencia del recurso fuera de scope.
            raise ApiError(
                status_code=404,
                code="NOT_FOUND",
                message="Recurso inexistente o fuera de alcance.",
            )
        return ctx

    return _dep
