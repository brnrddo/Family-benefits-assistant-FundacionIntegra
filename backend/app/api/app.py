"""App FastAPI del Rol 2 (FEAT-003; API-001/API-004/API-013).

- Monta los 6 routers con prefijo ``/api/v1``.
- Expone ``GET /healthz`` (200 simple).
- Sirve el contrato C3 como OpenAPI oficial en ``/api/v1/openapi.yaml`` (y lo usa
  en ``/docs``): el YAML del contrato es la FUENTE DE VERDAD; no se regenera el
  schema desde los modelos Pydantic.
- Logs sanitizados: solo request_id, método, ruta normalizada (plantilla, sin
  IDs), status y latencia; NUNCA body/prompt/respuesta/identificadores
  completos/tokens. El access log de uvicorn pasa por ``FiltroAccessLog``.
- Con ``E3_MOCK=0`` precalienta el snapshot del motor real al arrancar.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from app.api import motor_real
from app.api.deps import mock_habilitado, nuevo_request_id
from app.api.errors import registrar_handlers
from app.api.routers import (
    antecedentes,
    catalogo,
    familias,
    genai,
    jardines,
    kpi,
    tracking,
)

logger = logging.getLogger("app.api")

_API_PREFIX = "/api/v1"

# Ruta del contrato C3 (autoridad del OpenAPI). backend/app/api -> repo.
_REPO_DIR = Path(__file__).resolve().parent.parent.parent.parent
_C3_PATH = _REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts" / "C3-api.openapi.yaml"


def _cargar_c3_openapi() -> dict:
    """Carga el contrato C3 (YAML) como dict para servirlo tal cual."""
    with _C3_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Precalienta el snapshot del motor real (``E3_MOCK=0``) al arrancar.

    Nunca rompe el arranque: si el motor no está disponible, ``obtener_snapshot``
    ya registró el motivo y las rutas degradan a mocks.
    """
    if not mock_habilitado():
        try:
            motor_real.obtener_snapshot()
        except Exception:  # noqa: BLE001 - el arranque no depende del motor
            logger.warning("precalentamiento_motor_fallido")
    yield


def _ruta_normalizada(request: Request) -> str:
    """Plantilla de la ruta (``/api/v1/familias/{id}``), nunca el ID real."""
    ruta = getattr(request.scope.get("route"), "path", None)
    return ruta if isinstance(ruta, str) else "unmatched"


class FiltroAccessLog(logging.Filter):
    """Sanitiza el access log propio de uvicorn (``uvicorn.access``).

    uvicorn registra ``'%s - "%s %s HTTP/%s" %d'`` con la URL completa (IDs de
    familia y query libre). Por allowlist positiva, el filtro deja solo los
    segmentos literales de las rutas de la app; cualquier otro segmento pasa a
    ``{id}`` y la query se descarta. Así el log no depende de ``--no-access-log``.
    """

    def __init__(self, segmentos_literales: frozenset[str]) -> None:
        super().__init__()
        self._literales = segmentos_literales

    def sanitizar(self, ruta: str) -> str:
        sin_query = ruta.split("?", 1)[0]
        return "/".join(
            s if s == "" or s in self._literales else "{id}" for s in sin_query.split("/")
        ) or "/"

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            record.args = (args[0], args[1], self.sanitizar(args[2]), args[3], args[4])
        return True


def _segmentos_literales(app: FastAPI) -> frozenset[str]:
    """Segmentos fijos de todas las rutas montadas (sin parámetros ``{...}``)."""
    return frozenset(
        s
        for r in app.routes
        for s in str(getattr(r, "path", "")).split("/")
        if s and not s.startswith("{")
    )


def _instalar_filtro_access_log(app: FastAPI) -> None:
    access = logging.getLogger("uvicorn.access")
    for f in list(access.filters):
        if isinstance(f, FiltroAccessLog):
            access.removeFilter(f)
    access.addFilter(FiltroAccessLog(_segmentos_literales(app)))


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Brújula Familiar API",
        version="1.0.2",
        docs_url=None,       # servimos Swagger apuntando al contrato C3
        redoc_url=None,
        openapi_url=None,    # el OpenAPI oficial es el YAML del contrato
        lifespan=_lifespan,
    )

    # --- request_id + logging sanitizado ---------------------------------
    @app.middleware("http")
    async def _observabilidad(request: Request, call_next):
        request.state.request_id = nuevo_request_id()
        inicio = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latencia_ms = (time.perf_counter() - inicio) * 1000
            logger.exception(
                "api_error rid=%s method=%s path=%s latency_ms=%.1f",
                request.state.request_id, request.method, _ruta_normalizada(request),
                latencia_ms,
            )
            raise
        latencia_ms = (time.perf_counter() - inicio) * 1000
        logger.info(
            "api rid=%s method=%s path=%s status=%s latency_ms=%.1f",
            request.state.request_id, request.method, _ruta_normalizada(request),
            response.status_code, latencia_ms,
        )
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    registrar_handlers(app)

    # --- healthcheck -----------------------------------------------------
    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict:
        return {"status": "ok"}

    # --- OpenAPI oficial = contrato C3 -----------------------------------
    _c3 = _cargar_c3_openapi()

    @app.get(f"{_API_PREFIX}/openapi.json", include_in_schema=False)
    def openapi_json() -> JSONResponse:
        return JSONResponse(_c3)

    @app.get(f"{_API_PREFIX}/openapi.yaml", include_in_schema=False)
    def openapi_yaml() -> PlainTextResponse:
        return PlainTextResponse(
            yaml.safe_dump(_c3, allow_unicode=True, sort_keys=False),
            media_type="application/yaml",
        )

    @app.get("/docs", include_in_schema=False)
    def docs() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=f"{_API_PREFIX}/openapi.json",
            title="Brújula Familiar API — C3",
        )

    # --- routers bajo /api/v1 --------------------------------------------
    # ``antecedentes`` es la propuesta del Rol 3 (DEC-039): se sirve, pero NO
    # está en el contrato C3 1.0.2 que publica /docs (ver PROPUESTA_ANTECEDENTES.md).
    for modulo in (jardines, familias, antecedentes, tracking, genai, kpi, catalogo):
        app.include_router(modulo.router, prefix=_API_PREFIX)

    # Con todas las rutas montadas: el access log de uvicorn queda sanitizado.
    _instalar_filtro_access_log(app)
    return app


app = crear_app()
