"""Construcción de ``LlmContextV1`` por ALLOWLIST POSITIVA (FEAT-002).

Única puerta por la que puede pasar contexto hacia el LLM (spec §2.7.3,
PRIVACIDAD_DEMO). El objeto se arma campo por campo desde C1/C2 ya
autorizados; **nunca** se "limpia" por exclusión. Antes de devolver nada:

  1. se construye el dict solo con las claves permitidas del schema cerrado,
  2. se ejecuta ``contiene_campo_prohibido`` sobre el payload final (barrera
     defensiva: si alguna PII se coló por un valor anidado, se aborta),
  3. se valida contra ``LlmContextV1.schema.json`` con jsonschema.

Cualquier fuga o incoherencia lanza ``PiiLeakError`` y el flujo falla cerrado:
el llamador debe degradar a ``TemplateProvider``, nunca relajar campos.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.context.context_filter import CAMPOS_PROHIBIDOS, contiene_campo_prohibido

# Raíz del repo: backend/app/genai -> repo
_REPO_DIR = Path(__file__).resolve().parent.parent.parent.parent

_LLM_CONTEXT_SCHEMA_PATH = (
    _REPO_DIR
    / ".kiro"
    / "specs"
    / "_shared"
    / "contracts"
    / "schemas"
    / "LlmContextV1.schema.json"
)

# Enums cerrados del schema (allowlist de valores permitidos).
_ROLES_PERMITIDOS = {"ADULT_REFERENCE", "CHILD", "OTHER_ADULT"}
_RESULTADOS_PERMITIDOS = {"SI", "INDETERMINADO"}
_NIVELES_PERMITIDOS = {"CONFIRMADO", "PRELIMINAR", None}
_ESTADOS_ACCESO_PERMITIDOS = {
    "ASIGNADO", "GESTION_EN_CURSO", "GESTION_RECHAZADA",
    "ELEGIBLE_SIN_ASIGNACION", "SIN_CUPO", "PENDIENTE_ANTECEDENTES",
    "INDETERMINADO",
}
_RSH_BANDS_PERMITIDAS = {40, 50, 60, 70, 80, 90, 100, None}
_INCOME_BANDS_PERMITIDAS = {"UNDER_110K", "110K_250K", "250K_400K", "OVER_400K", None}
_FORMATOS_PERMITIDOS = {"TEXT", "VISUAL", "AUDIO"}


# Claves prohibidas adicionales específicas de esta barrera GenAI (dirección,
# contacto operativo, QR/códigos vinculables). Se SUMAN a las que ya vigila
# ``context_filter.CAMPOS_PROHIBIDOS`` (nombre, rut, folio, teléfono,
# nacionalidad, diagnóstico, salud…); aquí no se relaja ninguna, solo se amplía.
_CAMPOS_PROHIBIDOS_EXTRA = {
    "direccion", "dirección", "domicilio", "contacto", "celular",
    "qr", "codigo_qr", "código_qr", "codigo", "código", "codigos", "códigos",
    "patente", "ubicacion", "ubicación", "geo", "lat", "lon", "latitud", "longitud",
}
_CAMPOS_PROHIBIDOS_GENAI = CAMPOS_PROHIBIDOS | _CAMPOS_PROHIBIDOS_EXTRA


class PiiLeakError(Exception):
    """Se detectó (o pudo pasar) un dato prohibido rumbo al LLM: falla cerrado."""


def _buscar_prohibidos(obj) -> list[str]:
    """Como ``contiene_campo_prohibido`` pero con la allowlist ampliada GenAI."""
    encontrados: list[str] = contiene_campo_prohibido(obj)

    def _walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in _CAMPOS_PROHIBIDOS_EXTRA:
                    encontrados.append(str(k))
                _walk(v)
        elif isinstance(o, (list, tuple)):
            for item in o:
                _walk(item)

    _walk(obj)
    return encontrados


def _schema() -> dict:
    with _LLM_CONTEXT_SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _composition_desde_c2(c2_contexto_autorizado: dict) -> list[dict]:
    """Extrae SOLO role/age de la composición autorizada (allowlist positiva)."""
    salida: list[dict] = []
    for item in c2_contexto_autorizado.get("composition", []) or []:
        if not isinstance(item, dict):
            raise PiiLeakError("composition contiene un elemento no estructurado")
        role = item.get("role")
        age = item.get("age")
        if role not in _ROLES_PERMITIDOS:
            raise PiiLeakError(f"role fuera de allowlist: {role!r}")
        if not isinstance(age, int) or isinstance(age, bool):
            raise PiiLeakError("age debe ser entero")
        salida.append({"role": role, "age": age})
    return salida


def _benefit_desde_c1(entrada: dict) -> dict:
    """Mapea un beneficio autorizado al subobjeto cerrado del schema.

    Solo copia las claves de la allowlist; cualquier otra clave se ignora
    (nunca se arrastra). Los valores se validan contra los enums cerrados.
    """
    benefit_id = entrada.get("benefit_id")
    if not isinstance(benefit_id, str) or not benefit_id:
        raise PiiLeakError("benefit_id ausente o no es string")

    result = entrada.get("result")
    if result not in _RESULTADOS_PERMITIDOS:
        raise PiiLeakError(f"result fuera de allowlist: {result!r}")

    level = entrada.get("level")
    if level not in _NIVELES_PERMITIDOS:
        raise PiiLeakError(f"level fuera de allowlist: {level!r}")

    access_state = entrada.get("access_state")
    if access_state not in _ESTADOS_ACCESO_PERMITIDOS:
        raise PiiLeakError(f"access_state fuera de allowlist: {access_state!r}")

    reason_codes = list(entrada.get("reason_codes", []) or [])
    missing_codes = list(entrada.get("missing_codes", []) or [])
    source_ids = list(entrada.get("source_ids", []) or [])

    amount = entrada.get("amount")
    if amount is not None and (not isinstance(amount, (int, float)) or isinstance(amount, bool)):
        raise PiiLeakError("amount debe ser número o null")

    return {
        "benefit_id": benefit_id,
        "result": result,
        "level": level,
        "access_state": access_state,
        "reason_codes": reason_codes,
        "missing_codes": missing_codes,
        "amount": amount,
        "source_ids": source_ids,
    }


def construir_llm_context(
    c1_resultados: list[dict],
    c2_contexto_autorizado: dict,
    benefits: list[dict],
) -> dict:
    """Arma un ``LlmContextV1`` válido por allowlist positiva.

    - ``c2_contexto_autorizado``: vista ya minimizada (composition, rsh_band,
      income_band, preferred_format, language). Solo se copian esas claves.
    - ``benefits``: lista (1–3) de beneficios autorizados ya resueltos por el
      motor (C1), de los que se extrae el subobjeto cerrado.
    - ``c1_resultados``: se acepta para firma/trazabilidad; los campos que
      viajan salen de ``benefits`` (allowlist), no de C1 crudo.

    Lanza ``PiiLeakError`` ante cualquier valor fuera de allowlist, cualquier
    clave prohibida en el payload final o si el schema cerrado no valida.
    """
    # Barrera previa: si las entradas C1/C2 traen claves prohibidas (nombre,
    # rut, folio, telefono, direccion, nacionalidad, diagnostico, salud, qr…),
    # fallar antes de intentar construir nada. No se "limpia" por exclusión; se
    # aborta. Esto protege contra PII incrustada como clave hermana en un item
    # de composición o de beneficio.
    fugas_entrada = _buscar_prohibidos(c2_contexto_autorizado)
    for b in (benefits or []):
        fugas_entrada += _buscar_prohibidos(b)
    for r in (c1_resultados or []):
        fugas_entrada += _buscar_prohibidos(r)
    if fugas_entrada:
        raise PiiLeakError(
            f"entrada C1/C2 contiene claves prohibidas: {sorted(set(fugas_entrada))}"
        )

    rsh_band = c2_contexto_autorizado.get("rsh_band")
    if rsh_band not in _RSH_BANDS_PERMITIDAS:
        raise PiiLeakError(f"rsh_band fuera de allowlist: {rsh_band!r}")

    income_band = c2_contexto_autorizado.get("income_band")
    if income_band not in _INCOME_BANDS_PERMITIDAS:
        raise PiiLeakError(f"income_band fuera de allowlist: {income_band!r}")

    preferred_format = c2_contexto_autorizado.get("preferred_format")
    if preferred_format not in _FORMATOS_PERMITIDOS:
        raise PiiLeakError(f"preferred_format fuera de allowlist: {preferred_format!r}")

    language = c2_contexto_autorizado.get("language")
    if not isinstance(language, str):
        raise PiiLeakError("language ausente o no es string")

    payload = {
        "composition": _composition_desde_c2(c2_contexto_autorizado),
        "rsh_band": rsh_band,
        "income_band": income_band,
        "preferred_format": preferred_format,
        "language": language,
        "benefits": [_benefit_desde_c1(b) for b in (benefits or [])],
    }

    # Barrera defensiva: ninguna clave prohibida puede sobrevivir en el payload
    # final (incluye claves anidadas que un valor hostil pudiera arrastrar).
    fugas = _buscar_prohibidos(payload)
    if fugas:
        raise PiiLeakError(f"payload LLM contiene claves prohibidas: {sorted(set(fugas))}")

    # Validación de forma contra el schema cerrado (allowlist estructural).
    try:
        jsonschema.validate(payload, _schema())
    except jsonschema.ValidationError as exc:
        raise PiiLeakError(f"LlmContextV1 no cumple el schema cerrado: {exc.message}") from exc

    return payload
