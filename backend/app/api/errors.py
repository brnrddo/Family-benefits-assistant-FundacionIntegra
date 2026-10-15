"""Errores cerrados conforme a ``ErrorResponse.schema.json`` (FEAT-003; API-004/API-013).

Todas las rutas devuelven exactamente el shape
``{"error": {code, message, request_id, retryable, details[]}}``. Los mensajes
NUNCA ecoan valores de entrada ni PII: son textos fijos y genéricos.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# request_id se construye perezosamente para no importar deps (evita ciclo).

# Códigos canónicos por status (patrón ^[A-Z][A-Z0-9_]+$).
_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE",
    429: "THROTTLED",
    503: "UNAVAILABLE",
}

# Mensajes genéricos (sin eco de entrada ni PII).
_MESSAGE_BY_STATUS = {
    400: "Solicitud mal formada.",
    401: "Autenticación ausente o inválida.",
    403: "Operación no permitida.",
    404: "Recurso inexistente o fuera de alcance.",
    409: "Conflicto de idempotencia, snapshot o asset.",
    422: "Entrada semánticamente inválida.",
    429: "Demasiadas solicitudes.",
    503: "Dependencia no disponible.",
}

# status que admiten reintento del cliente.
_RETRYABLE_STATUS = frozenset({429, 503})


def _es_retryable(status: int) -> bool:
    return status in _RETRYABLE_STATUS


class ApiError(Exception):
    """Error tipado que se serializa al shape cerrado de ``ErrorResponse``."""

    def __init__(
        self,
        status_code: int,
        code: str | None = None,
        message: str | None = None,
        details: list[dict] | None = None,
        retryable: bool | None = None,
    ):
        self.status_code = status_code
        self.code = code or _CODE_BY_STATUS.get(status_code, "ERROR")
        self.message = message or _MESSAGE_BY_STATUS.get(status_code, "Error.")
        self.details = details or []
        self.retryable = _es_retryable(status_code) if retryable is None else retryable
        super().__init__(self.message)


def _request_id(request: Request) -> str:
    from app.api.deps import nuevo_request_id

    rid = getattr(request.state, "request_id", None)
    return rid or nuevo_request_id()


def _payload(request: Request, status: int, code: str, message: str,
             retryable: bool, details: list[dict]) -> dict:
    return {
        "error": {
            "code": code,
            "message": message[:200],
            "request_id": _request_id(request),
            "retryable": retryable,
            "details": details[:20],
        }
    }


def _json(request: Request, status: int, code: str, message: str,
          retryable: bool, details: list[dict]) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=_payload(request, status, code, message, retryable, details),
    )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _json(request, exc.status_code, exc.code, exc.message, exc.retryable, exc.details)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    status = exc.status_code
    code = _CODE_BY_STATUS.get(status, "ERROR")
    message = _MESSAGE_BY_STATUS.get(status, "Error.")
    retryable = _es_retryable(status)
    return _json(request, status, code, message, retryable, [])


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic/validación de request -> 422 con el shape cerrado.

    Solo se expone la RUTA del campo y una razón genérica; nunca el valor
    recibido (evita ecoar PII o entrada del cliente).
    """
    details: list[dict] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        # loc típicamente arranca con 'body'/'query'/'path'; se normaliza a texto.
        field = ".".join(str(p) for p in loc) or "body"
        details.append({"field": field[:120], "reason": "Campo inválido o ausente."})
    return _json(request, 422, "UNPROCESSABLE", _MESSAGE_BY_STATUS[422], False, details)


def registrar_handlers(app) -> None:
    """Registra los exception handlers que cierran el shape de error."""
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
