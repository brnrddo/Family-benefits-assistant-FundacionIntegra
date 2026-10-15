"""App FastAPI del Rol 2 (FEAT-003; API-001/API-004/API-013).

- Monta los 6 routers con prefijo ``/api/v1``.
- Expone ``GET /healthz`` (200 simple).
- Sirve el contrato C3 como OpenAPI oficial en ``/api/v1/openapi.yaml`` (y lo usa
  en ``/docs``): el YAML del contrato es la FUENTE DE VERDAD; no se regenera el
  schema desde los modelos Pydantic.
- Logs sanitizados: solo request_id, método, ruta, status y latencia; NUNCA
  body/prompt/respuesta/identificadores completos/tokens.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from app.api.deps import nuevo_request_id
from app.api.errors import registrar_handlers
from app.api.routers import (
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


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Brújula Familiar API",
        version="1.0.2",
        docs_url=None,       # servimos Swagger apuntando al contrato C3
        redoc_url=None,
        openapi_url=None,    # el OpenAPI oficial es el YAML del contrato
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
                request.state.request_id, request.method, request.url.path, latencia_ms,
            )
            raise
        latencia_ms = (time.perf_counter() - inicio) * 1000
        logger.info(
            "api rid=%s method=%s path=%s status=%s latency_ms=%.1f",
            request.state.request_id, request.method, request.url.path,
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
    for modulo in (jardines, familias, tracking, genai, kpi, catalogo):
        app.include_router(modulo.router, prefix=_API_PREFIX)

    return app


app = crear_app()
