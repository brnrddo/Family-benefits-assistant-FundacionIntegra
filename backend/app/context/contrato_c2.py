"""Adaptador del `contexto_familia` interno al contrato C2 formal.

El Rol 1 construye `contexto_familia` con claves internas en español
(`contexto_familia.py`, redacción §2.7.2). El contrato que CONSUME el Rol 2 y el
frontend es el schema versionado `urn:brujula:c2:contexto-familia:v1`
(`.kiro/specs/_shared/contracts/C2-contexto-familia.schema.json`), con otra
forma: `hechos[]` tipados, `procedencia[]`, `data_classification`, vocabulario
cerrado en inglés (`rsh.band`, `income.per_capita_band`, `composition`...),
roles `ADULTA_REFERENCIA/NINO_JARDIN/OTRO_ADULTO` y señales con nombres propios.

Este módulo traduce interno -> contrato SIN tocar el builder (no invasivo). La
traducción de nombres vive aquí a propósito: el contrato NO se renombra (lo
consumen Rol 2 y Rol 3); es el Rol 1 quien se adapta al contrato.

No decide elegibilidad ni añade datos: solo reempaqueta lo que el builder ya
derivó, mapeando vocabularios y descartando lo que el contrato no admite.
"""
from __future__ import annotations

from .ficha_sintetica import NO_INFORMADO

DATA_CLASSIFICATION = "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"

# rol interno -> rol del contrato (enum miembroComposicion).
_ROL_CONTRATO = {
    "ADULTA_REFERENCIA": "ADULTA_REFERENCIA",
    "PAREJA": "ADULTA_REFERENCIA",
}

# rango de ingreso interno -> enum income.per_capita_band del contrato.
_INGRESO_CONTRATO = {
    "MENOS_110K": "UNDER_110K",
    "ENTRE_110K_250K": "110K_250K",
    "ENTRE_250K_400K": "250K_400K",
    "MAS_400K": "OVER_400K",
}

# fuente interna (de la ficha) -> enum `fuente` del contrato.
_FUENTE_CONTRATO = {
    "FICHA_SINTETICA": "FICHA_SINTETICA",
    "FICHA_DIGITAL": "FICHA_DIGITAL",
}


def _rol_contrato(miembro: dict) -> str:
    if miembro.get("es_nino_jardin"):
        return "NINO_JARDIN"
    return _ROL_CONTRATO.get(miembro.get("rol"), "OTRO_ADULTO")


def _rsh_band(tramo) -> int | None:
    try:
        v = int(tramo)
    except (TypeError, ValueError):
        return None
    return v if v in (40, 50, 60, 70, 80, 90, 100) else None


def a_contrato_c2(ctx: dict) -> dict:
    """Convierte el `contexto_familia` interno al contrato C2 v1.

    `ctx` es la salida de `construir_contexto`. Devuelve un dict que valida
    contra `C2-contexto-familia.schema.json`.
    """
    hechos: list[dict] = []
    procedencia: list[dict] = []

    def _agregar(campo: str, valor, estado_dato: str, acreditada: bool, fuente: str):
        hechos.append({
            "campo": campo, "valor": valor,
            "estado_dato": estado_dato, "acreditada": acreditada,
        })
        procedencia.append({"campo": campo, "fuente": fuente})

    # --- composition (roles + edades, sin nombres) ---------------------------
    composicion = [
        {"rol": _rol_contrato(m), "edad": m.get("edad")}
        for m in ctx.get("composicion", [])
        if m.get("edad") is not None  # el contrato exige edad entera 0..120
    ]
    _agregar("composition", composicion or None,
             "OBSERVADO", True, "DATASET_E3")

    # --- rsh.has_registry + rsh.band -----------------------------------------
    rsh = ctx.get("rsh") or {}
    _agregar("rsh.has_registry", bool(rsh.get("tiene")),
             "OBSERVADO", True, "DATASET_E3")
    band = _rsh_band(rsh.get("tramo"))
    _agregar("rsh.band", band, "OBSERVADO", band is not None, "DATASET_E3")

    # --- income.per_capita_band ----------------------------------------------
    rango = ctx.get("ingreso_per_capita_rango")
    income = _INGRESO_CONTRATO.get(rango)
    _agregar("income.per_capita_band", income,
             "OBSERVADO", income is not None, "DATASET_E3")

    # --- señales de vulnerabilidad (solo lo que el contrato admite) ----------
    sv_in = ctx.get("senales_vulnerabilidad", {})
    prevision = sv_in.get("fonasa_tramo")
    senales_vuln = {
        "prevision_salud": "NO_INFORMADO" if prevision in (None, NO_INFORMADO) else prevision,
        "puntaje_cse": None if sv_in.get("puntaje_cse") in (None, NO_INFORMADO) else sv_in.get("puntaje_cse"),
        "jefa_hogar_sernameg": None if sv_in.get("jefa_hogar_sernameg") in (None, NO_INFORMADO) else sv_in.get("jefa_hogar_sernameg"),
        "posible_discapacidad_nino": ctx.get("posible_discapacidad_nino")
        if isinstance(ctx.get("posible_discapacidad_nino"), bool) else None,
    }

    # --- señales de urgencia --------------------------------------------------
    su_in = ctx.get("senales_urgencia", {})
    inseg = su_in.get("inseguridad_alimentaria")
    senales_urg = {
        "emergencia_reciente": su_in.get("evento_emergencia")
        if isinstance(su_in.get("evento_emergencia"), bool) else None,
        "inseguridad_alimentaria_nivel": int(inseg) if isinstance(inseg, (int, float)) else None,
        "vivienda_precaria": su_in.get("vivienda_precaria")
        if isinstance(su_in.get("vivienda_precaria"), bool) else None,
    }

    idioma = ctx.get("idioma_mensaje") or "es"
    formato = ctx.get("formato_preferido") or "TEXTO"

    return {
        "data_classification": DATA_CLASSIFICATION,
        "id_familia": ctx["id_familia"],
        "fuente": _FUENTE_CONTRATO.get(ctx.get("fuente"), "FICHA_SINTETICA"),
        "hechos": hechos,
        "procedencia": procedencia,
        "inconsistencias": [],   # el formato de inconsistencias del contrato es
                                 # un enum cerrado distinto del interno; no se
                                 # fuerza (se puebla cuando haya FICHA_DIGITAL).
        "no_informado": [],
        "senales_urgencia": senales_urg,
        "senales_vulnerabilidad": senales_vuln,
        "formato_preferido": formato if formato in ("TEXTO", "VISUAL", "AUDIO") else "TEXTO",
        "idioma_mensaje": idioma,
    }
