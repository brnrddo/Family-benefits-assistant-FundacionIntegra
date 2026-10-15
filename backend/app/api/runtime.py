"""Capa de servicio: genai por plantilla e integración opcional del motor (FEAT-003).

- La generación de texto (guion/mensaje/asistente) usa SIEMPRE el
  ``TemplateProvider`` determinista de FEAT-002 (``provider='PLANTILLA'``),
  construido desde el catálogo C4 provisional. El cliente nunca envía contexto,
  catálogo ni prompt (API-007).
- La integración del motor (FEAT-001 priority + FEAT-002 filtro) vive detrás de
  la bandera ``E3_MOCK``. Por defecto (``E3_MOCK=1``) todo es mock. Con
  ``E3_MOCK=0`` se intenta tocar la DB; si falta, se degrada a mocks con un
  warning sanitizado y NUNCA se rompe (no hay 500).
"""
from __future__ import annotations

import logging

from app.api.deps import DISCLAIMER, construir_meta, mock_habilitado
from app.config import DB_PATH
from app.genai import (
    TemplateError,
    TemplateProvider,
    catalogo_desde_benefits,
)
from app.priority import ConfigInvalida, cargar_ranking_config

logger = logging.getLogger("app.api")

# Catálogo del TemplateProvider construido una vez desde el bundle C4.
_provider: TemplateProvider | None = None


def _cargar_catalogo() -> dict:
    """Lee BENEFITS + I18N del bundle C4 mock del Rol 2 y arma el catálogo."""
    import json
    from pathlib import Path

    from app.priority.config import _DEFAULT_MANIFEST  # ruta por defecto validada

    # Las rutas del catálogo se resuelven contra el directorio del manifest por
    # defecto, no contra la raíz del repo: el bundle es relocalizable (DEC-022).
    # El catálogo NO sigue E3_CONTENT_MANIFEST: siempre lee el mock del Rol 2.
    bundle_dir = Path(_DEFAULT_MANIFEST).resolve().parent
    benefits_path = bundle_dir / "benefits.json"
    i18n_path = bundle_dir / "i18n" / "es.json"

    with benefits_path.open(encoding="utf-8") as fh:
        benefits = json.load(fh).get("benefits", [])
    with i18n_path.open(encoding="utf-8") as fh:
        i18n = json.load(fh)

    # El catálogo exige where_to_go/reason/action; se completan con copy simple
    # y neutro (español de usted) desde el i18n cuando existe.
    enriquecidos: list[dict] = []
    for b in benefits:
        enriquecidos.append({
            "benefit_id": b["benefit_id"],
            "title_key": b.get("title_key", ""),
            "reason": "Según el catálogo, podría corresponderle este apoyo.",
            "action": "Vale la pena consultar los requisitos en la institución.",
            "where_to_go": "Oficina de ChileAtiende de su comuna.",
            "source_id": b.get("source_id", "SRC-OFICIAL"),
            "source_url": b.get("source_url", ""),
        })
    return catalogo_desde_benefits(enriquecidos, i18n)


def get_provider() -> TemplateProvider:
    """Devuelve el ``TemplateProvider`` (catálogo C4) construyéndolo perezosamente."""
    global _provider
    if _provider is None:
        _provider = TemplateProvider(_cargar_catalogo())
    return _provider


def _ids_autorizados(provider: TemplateProvider, benefit_ids: list[str]) -> list[str]:
    """Filtra a los benefit_ids con respaldo en el catálogo C4.

    El request público solo trae IDs; el servidor valida que existan en el
    catálogo autorizado (API-007). IDs sin respaldo se descartan.
    """
    validos: list[str] = []
    for bid in benefit_ids:
        if bid in provider._catalogo:  # noqa: SLF001 (acceso controlado interno)
            validos.append(bid)
    return validos


def generar_guion(benefit_ids: list[str], request_id: str) -> dict:
    """Arma el ``ScriptGenerationEnvelope`` C3 (provider=PLANTILLA)."""
    provider = get_provider()
    ids = _ids_autorizados(provider, benefit_ids)
    try:
        content = provider.generar_guion(ids)
        warnings: list[str] = []
    except TemplateError:
        # Fallback cerrado: sin respaldo, se usa el primer beneficio del catálogo.
        content = provider.generar_guion(list(provider._catalogo)[:1])  # noqa: SLF001
        warnings = ["FALLBACK_TEMPLATE"]
    return {
        "meta": construir_meta(request_id),
        "provider": provider.provider,
        "warnings": warnings,
        "content": content,
        "disclaimer": DISCLAIMER,
    }


def generar_mensaje(benefit_ids: list[str], request_id: str) -> dict:
    """Arma el ``MessageGenerationEnvelope`` C3 (provider=PLANTILLA)."""
    provider = get_provider()
    ids = _ids_autorizados(provider, benefit_ids)
    try:
        content = provider.generar_mensaje(ids)
        warnings: list[str] = []
    except TemplateError:
        content = provider.generar_mensaje(list(provider._catalogo)[:1])  # noqa: SLF001
        warnings = ["FALLBACK_TEMPLATE"]
    return {
        "meta": construir_meta(request_id),
        "provider": provider.provider,
        "warnings": warnings,
        "content": content,
        "disclaimer": DISCLAIMER,
    }


def responder_asistente(question: str, request_id: str) -> dict:
    """Arma el ``AssistantEnvelope`` C3 (plantilla; sin Bedrock)."""
    provider = get_provider()
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
