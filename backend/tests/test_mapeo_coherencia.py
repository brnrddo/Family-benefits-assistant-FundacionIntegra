"""Coherencia entre el filtro C2 del Rol 1 y el contrato de privacidad del Rol 4.

`content/mapeo_ficha.csv` (dueño: Rol 4, "C0 definitivo" DEC-046) es la fuente
de verdad de qué campos pueden viajar al LLM: las filas con
`nivel_privacidad = CONTEXTO_MINIMO_LLM` y `permitido_llm = true`.

El filtro del Rol 1 (`context_filter.filtrar_para_llm`) usa un allowlist
hardcodeado. Si Rol 4 cambia el contrato en un futuro merge (agrega o quita un
campo permitido al LLM), este test DEBE fallar para que el Rol 1 lo reconcilie
en vez de divergir en silencio (dejar pasar un campo ya prohibido, o bloquear
uno recién permitido).

Nota de nombres: el CSV usa el vocabulario del contrato C2 formal
(`.kiro/specs/_shared/contracts/C2-contexto-familia.schema.json`), en inglés
(`child.age`, `rsh.band`, `income.per_capita_band`, `composition`). El Rol 1 usa
claves internas en español. El mapeo contrato->interno es explícito aquí; NO se
renombra el contrato (lo consumen Rol 2 y el frontend).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.context.context_filter import filtrar_para_llm

# Raíz del repo: backend/tests -> backend -> repo.
REPO_DIR = Path(__file__).resolve().parent.parent.parent
MAPEO_CSV = REPO_DIR / "content" / "mapeo_ficha.csv"

# Mapeo contrato C2 (campo_motor del CSV) -> clave de primer nivel que el filtro
# del Rol 1 deja pasar hacia el LLM. `child.age` no es una clave de primer nivel:
# viaja DENTRO de `composicion` (rol+edad), por eso mapea a "composicion".
CONTRATO_A_ALLOWLIST = {
    "composition": "composicion",
    "child.age": "composicion",            # edad por rol, dentro de composicion
    "income.per_capita_band": "ingreso_per_capita_rango",
    "rsh.band": "rsh",                     # el filtro deja pasar rsh.tramo
    "formato_preferido": "formato_preferido",
    "idioma_mensaje": "idioma_mensaje",
}


def _campos_motor_permitidos_llm() -> set[str]:
    """campo_motor distintos marcados CONTEXTO_MINIMO_LLM + permitido_llm=true."""
    with MAPEO_CSV.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    out = set()
    for r in filas:
        if (r["nivel_privacidad"] == "CONTEXTO_MINIMO_LLM"
                and r["permitido_llm"].strip().lower() == "true"
                and r["campo_motor"].strip()):
            out.add(r["campo_motor"].strip())
    return out


def test_mapeo_ficha_existe():
    assert MAPEO_CSV.is_file(), f"No se encontró {MAPEO_CSV}"


def test_contrato_llm_coincide_con_allowlist_del_rol1():
    """El contrato C2 (CSV) y lo que el filtro del Rol 1 deja pasar coinciden.

    Se prueba el COMPORTAMIENTO real de `filtrar_para_llm` (no una constante),
    porque algunas claves (p. ej. `rsh`) se filtran por un camino especial.

    Si falla: Rol 4 cambió qué va al LLM. Hay que reconciliar el filtro
    (`context_filter`) y, si aparece un campo_motor nuevo, extender
    CONTRATO_A_ALLOWLIST con su mapeo al nombre interno del Rol 1.
    """
    campos_csv = _campos_motor_permitidos_llm()

    # 1) Todo campo del CSV debe tener un mapeo conocido al vocabulario interno.
    sin_mapeo = campos_csv - set(CONTRATO_A_ALLOWLIST)
    assert not sin_mapeo, (
        "El contrato de Rol 4 permite al LLM campos sin mapeo en el Rol 1: "
        f"{sorted(sin_mapeo)}. Actualiza CONTRATO_A_ALLOWLIST y el filtro."
    )

    # 2) Claves internas que el contrato (CSV) dice que el LLM puede recibir.
    esperado_interno = {CONTRATO_A_ALLOWLIST[c] for c in campos_csv}

    # 3) Claves que el filtro REALMENTE deja pasar, con un contexto que trae
    #    todas las permitidas + varias prohibidas (para asegurar que se descartan).
    ctx_demo = {
        "id_familia": "FAM-X",                       # prohibido
        "composicion": [{"rol": "HIJO_HIJA", "edad": 5, "id": "INT-1"}],
        "rsh": {"tiene": True, "tramo": 40},
        "ingreso_per_capita_rango": "MENOS_110K",
        "formato_preferido": "TEXTO",
        "idioma_mensaje": "ES",
        "senales_vulnerabilidad": {"x": 1},          # prohibido
        "no_informado": ["y"],                        # prohibido
    }
    filtrado = set(filtrar_para_llm(ctx_demo).keys())

    assert filtrado == esperado_interno, (
        "Divergencia filtro Rol 1 vs contrato Rol 4.\n"
        f"  derivado del CSV : {sorted(esperado_interno)}\n"
        f"  deja pasar filtro: {sorted(filtrado)}"
    )


def test_sin_fugas_fuera_del_contexto_minimo():
    """Ninguna fila fuera de CONTEXTO_MINIMO_LLM puede tener permitido_llm=true.

    Protege el invariante del contrato: permitido_llm=true <=> CONTEXTO_MINIMO_LLM.
    """
    with MAPEO_CSV.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    fugas = [
        r["campo_origen"] for r in filas
        if r["permitido_llm"].strip().lower() == "true"
        and r["nivel_privacidad"] != "CONTEXTO_MINIMO_LLM"
    ]
    assert not fugas, f"Filas permitido_llm=true fuera de CONTEXTO_MINIMO_LLM: {fugas}"
