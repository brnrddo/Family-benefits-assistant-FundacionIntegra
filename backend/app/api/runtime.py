"""Capa de servicio: genai por plantilla e integración opcional del motor (FEAT-003).

- La generación de texto (guion/mensaje/asistente) usa por defecto el
  ``TemplateProvider`` determinista de FEAT-002 (``provider='PLANTILLA'``),
  construido desde el catálogo C4 de ``content/`` (Rol 4, DEC-055). El cliente
  nunca envía contexto, catálogo ni prompt (API-007).
- El guion y el mensaje tienen camino Bedrock, detrás de
  ``E3_LLM_PROVIDER=bedrock`` y delegado completo a ``app.genai.redaccion``
  (allowlist, envelope interno, Guardrails y postvalidación). Ante cualquier
  fallo se degrada a la plantilla con HTTP 200 y
  ``warnings=['GENAI_DEGRADADO_A_PLANTILLA']`` (API-008). ``/asistente`` sigue
  siempre por plantilla.
- Un ``benefit_id`` sin respaldo en el catálogo responde 422 y nunca se
  sustituye por otro beneficio (DEC-056). Si el catálogo no valida, la
  respuesta falla cerrada sin 500 (DEC-058).
- La integración del motor (FEAT-001 priority + FEAT-002 filtro) vive detrás de
  la bandera ``E3_MOCK``. Por defecto (``E3_MOCK=1``) todo es mock. Con
  ``E3_MOCK=0`` se intenta tocar la DB; si falta, se degrada a mocks con un
  warning sanitizado y NUNCA se rompe (no hay 500).
"""
from __future__ import annotations

import logging
import threading

from app.api.deps import DISCLAIMER, construir_meta, mock_habilitado
from app.api.errors import ApiError
from app.config import DB_PATH
from app.genai import (
    TemplateError,
    TemplateProvider,
    asistente_sin_catalogo,
    content_catalog,
    redaccion,
)
from app.genai.template_provider import (
    GUION_SIN_CATALOGO,
    WARNING_SIN_CATALOGO,
)
from app.priority import ConfigInvalida, cargar_ranking_config

logger = logging.getLogger("app.api")

# TemplateProvider construido una vez desde content/ (solo si valida).
_provider: TemplateProvider | None = None
_provider_lock = threading.Lock()

WARNING_SECCION_OMITIDA = "SECCION_SIN_FUENTE_OMITIDA"
# El camino Bedrock falló de forma recuperable y respondió la plantilla (API-008).
WARNING_GENAI_DEGRADADO = "GENAI_DEGRADADO_A_PLANTILLA"

_RAZON_DESCONOCIDO = "Beneficio sin respaldo en el catálogo C4."
_RAZON_SIN_FUENTE = "Beneficio sin fuente oficial para la tarjeta."


def _log_sin_catalogo(motivo: str) -> None:
    # Solo el código fijo: sin rutas, IDs, preguntas ni textos.
    logger.warning("catalogo_c4_no_disponible: motivo=%s", motivo)


def _log_genai_degradado(motivo: str) -> None:
    # Misma convención que motor_real ``runtime_degradado_a_mock``: solo el
    # código fijo, nunca el prompt, la salida del modelo ni valores.
    logger.warning("genai_degradado_a_plantilla: motivo=%s", motivo)


def get_provider() -> TemplateProvider | None:
    """``TemplateProvider`` con el catálogo C4 de ``content/``, o ``None``.

    Se construye perezosamente y se cachea solo si el catálogo valida; un fallo
    no se cachea, así el siguiente request reintenta la carga.
    """
    global _provider
    if _provider is not None:
        return _provider
    with _provider_lock:
        if _provider is None:
            try:
                cat = content_catalog.cargar_catalogo_contenido()
            except content_catalog.ContenidoInvalido as exc:
                _log_sin_catalogo(exc.codigo)
                return None
            _provider = TemplateProvider(cat.entradas, cat.plantillas)
    return _provider


def _detalles(benefit_ids: list[str], razon: str, incluir) -> list[dict]:
    """``details`` de ErrorResponse por índice, nunca con el valor recibido."""
    return [
        {"field": f"body.benefit_ids.{i}", "reason": razon}
        for i, bid in enumerate(benefit_ids) if incluir(bid)
    ]


def _exigir_conocidos(provider: TemplateProvider, benefit_ids: list[str]) -> None:
    """422 si algún ``benefit_id`` no está en el catálogo C4 (DEC-056)."""
    detalles = _detalles(benefit_ids, _RAZON_DESCONOCIDO, lambda b: not provider.conoce(b))
    if detalles:
        raise ApiError(status_code=422, details=detalles, retryable=False)


def _envelope(request_id: str, content: dict, warnings: list[str],
              provider: str = TemplateProvider.provider) -> dict:
    return {
        "meta": construir_meta(request_id),
        "provider": provider,
        "warnings": warnings,
        "content": content,
        "disclaimer": DISCLAIMER,
    }


def _vista_familia_llm(family_id: str | None) -> dict | None:
    """Ficha de la familia (motor real o mock) para armar el contexto del LLM.

    Solo lectura: con ``E3_MOCK=0`` es el snapshot compartido e inmutable. El
    import es diferido porque ``motor_real`` importa este módulo y a nivel de
    módulo sería circular.
    """
    if family_id is None:
        return None
    from app.api import mock_data, motor_real

    snap = motor_real.obtener_snapshot()
    if snap is not None:
        return snap.familias.get(family_id)
    return mock_data.FAMILIAS.get(family_id)


def _guion_sin_catalogo(benefit_ids: list[str], request_id: str) -> dict:
    """Guion fijo sin nombre de ningún beneficio (DEC-058)."""
    content = {
        "benefit_ids": list(dict.fromkeys(benefit_ids))[:3],
        "script": f"{GUION_SIN_CATALOGO} {DISCLAIMER}",
    }
    return _envelope(request_id, content, [WARNING_SIN_CATALOGO])


def generar_guion(benefit_ids: list[str], request_id: str,
                  family_id: str | None = None) -> dict:
    """Arma el ``ScriptGenerationEnvelope`` C3 (PLANTILLA o BEDROCK).

    Con ``E3_LLM_PROVIDER=bedrock`` se intenta redactar con el modelo; ante
    cualquier fallo del camino Bedrock se degrada a la plantilla determinista
    con HTTP 200 y un warning de código fijo (API-008). Sin esa bandera el
    comportamiento es exactamente el de antes.
    """
    provider = get_provider()
    if provider is None:
        return _guion_sin_catalogo(benefit_ids, request_id)
    _exigir_conocidos(provider, benefit_ids)
    warnings: list[str] = []
    if redaccion.bedrock_seleccionado():
        try:
            content = redaccion.redactar_guion(
                benefit_ids, _vista_familia_llm(family_id), request_id=request_id
            )
            return _envelope(request_id, content, [], provider=redaccion.PROVIDER_BEDROCK)
        except redaccion.RedaccionError as exc:
            _log_genai_degradado(exc.motivo)
            warnings = [WARNING_GENAI_DEGRADADO]
    try:
        content = provider.generar_guion(benefit_ids)
    except TemplateError:
        # Invariante roto tras validar: se responde sin texto de beneficios.
        _log_sin_catalogo("INVARIANTE_PLANTILLA")
        return _guion_sin_catalogo(benefit_ids, request_id)
    return _envelope(request_id, content, warnings)


def _warnings_mensaje(content: dict) -> list[str]:
    """Warning si algún beneficio pedido quedó sin sección (PREG-045)."""
    omitidas = len(content["benefit_ids"]) > len(content["printable_card"]["sections"])
    return [WARNING_SECCION_OMITIDA] if omitidas else []


def generar_mensaje(benefit_ids: list[str], request_id: str,
                    family_id: str | None = None) -> dict:
    """Arma el ``MessageGenerationEnvelope`` C3 (PLANTILLA o BEDROCK).

    Sin catálogo no hay tarjeta válida (C3 exige citas): 503. Los beneficios
    sin fuente oficial (PREG-045) no llevan sección y se avisa con un warning;
    si ninguno la tiene, 422 (DEC-057).

    Con ``E3_LLM_PROVIDER=bedrock`` el modelo escribe el preview y el
    ``reason``/``action`` de cada sección; todo lo demás (orden, títulos,
    lugares y citas) lo pone el servidor. Cualquier fallo degrada a la
    plantilla con HTTP 200 y un warning de código fijo (API-008).
    """
    provider = get_provider()
    if provider is None:
        raise ApiError(status_code=503)
    _exigir_conocidos(provider, benefit_ids)
    if not any(provider.tiene_cita(bid) for bid in benefit_ids):
        detalles = _detalles(benefit_ids, _RAZON_SIN_FUENTE, lambda b: True)
        raise ApiError(status_code=422, details=detalles, retryable=False)
    warnings: list[str] = []
    if redaccion.bedrock_seleccionado():
        try:
            content = redaccion.redactar_mensaje(
                benefit_ids, _vista_familia_llm(family_id), request_id=request_id
            )
            return _envelope(
                request_id, content, _warnings_mensaje(content),
                provider=redaccion.PROVIDER_BEDROCK,
            )
        except redaccion.RedaccionError as exc:
            _log_genai_degradado(exc.motivo)
            warnings = [WARNING_GENAI_DEGRADADO]
    try:
        content = provider.generar_mensaje(benefit_ids)
    except TemplateError:
        _log_sin_catalogo("INVARIANTE_PLANTILLA")
        raise ApiError(status_code=503) from None
    return _envelope(request_id, content, warnings + _warnings_mensaje(content))


def responder_asistente(question: str, request_id: str) -> dict:
    """Arma el ``AssistantEnvelope`` C3 (plantilla; sin Bedrock)."""
    provider = get_provider()
    if provider is None:
        return asistente_sin_catalogo(request_id, question)
    return provider.responder_asistente(request_id, question)


# --- Integración opcional del motor (E3_MOCK=0) ------------------------------


def runtime_disponible() -> bool:
    """True si NO estamos en modo mock Y la DB del motor existe.

    Con ``E3_MOCK=0`` y DB ausente, degradamos a mocks (devolvemos False) sin
    romper. El warning se registra sanitizado (sin cuerpos ni PII).
    """
    if mock_habilitado():
        return False
    if not DB_PATH.exists():
        logger.warning("runtime_degradado_a_mock: DB del motor no disponible")
        return False
    try:
        # Validar que el bundle C4 cargue; si no, también degradamos.
        cargar_ranking_config()
    except ConfigInvalida:
        logger.warning("runtime_degradado_a_mock: bundle C4 inválido")
        return False
    return True


def warnings_runtime() -> list[str]:
    """Warnings a adjuntar en respuestas GET cuando se pidió runtime pero se degradó."""
    if not mock_habilitado() and not runtime_disponible():
        return ["RUNTIME_DEGRADADO_A_MOCK"]
    return []
