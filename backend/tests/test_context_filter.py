"""Tests del contrato C2 (contexto_familia) y del filtro hacia el LLM (§2.7).

El test del filtro FALLA si aparece un campo prohibido en lo que iría al LLM.
"""
from __future__ import annotations

import pytest

from app.context import construir_contexto, construir_ficha, filtrar_para_llm
from app.context.context_filter import (CAMPOS_PERMITIDOS_LLM,
                                        contiene_campo_prohibido)


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


FAM = "FAM-SIM-E3-00100"


# --- contrato C2 (§2.7.2): forma exacta --------------------------------------

def test_contexto_tiene_claves_del_contrato(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    esperadas = {
        "id_familia", "fuente", "composicion", "rsh", "ingreso_per_capita_rango",
        "senales_vulnerabilidad", "senales_urgencia", "posible_discapacidad_nino",
        "formato_preferido", "idioma_mensaje", "inconsistencias", "no_informado",
        "calidad_datos",
    }
    assert esperadas.issubset(set(ctx.keys()))


def test_composicion_solo_rol_y_edad(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    assert ctx["composicion"], "composición no debe ir vacía"
    for item in ctx["composicion"]:
        assert set(item.keys()) == {"rol", "edad"}


def test_rango_ingreso_es_categoria(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    assert ctx["ingreso_per_capita_rango"] in {
        "MENOS_110K", "ENTRE_110K_250K", "ENTRE_250K_400K", "MAS_400K", "NO_INFORMADO"}


def test_ficha_marca_no_informado(conn, fecha):
    ficha = construir_ficha(FAM, conn=conn, fecha=fecha)
    # Campos que el dataset no trae deben quedar NO_INFORMADO (no inventados).
    assert ficha["prevision_salud"] == "NO_INFORMADO"
    assert ficha["vivienda"] == "NO_INFORMADO"


# --- filtro hacia el LLM (§2.7.3): el test clave de privacidad ---------------

def test_filtro_solo_deja_campos_permitidos(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    filtrado = filtrar_para_llm(ctx)
    permitidas = CAMPOS_PERMITIDOS_LLM | {"rsh"}
    assert set(filtrado.keys()).issubset(permitidas)
    # rsh solo con tramo.
    if "rsh" in filtrado:
        assert set(filtrado["rsh"].keys()) == {"tramo"}


def test_filtro_sin_campos_prohibidos(conn, fecha):
    """FALLA si aparece cualquier campo prohibido en la salida filtrada."""
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    filtrado = filtrar_para_llm(ctx)
    fugas = contiene_campo_prohibido(filtrado)
    assert fugas == [], f"Campos prohibidos en lo que iría al LLM: {fugas}"


def test_filtro_no_muta_el_contexto_original(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    antes = set(ctx.keys())
    filtrar_para_llm(ctx)
    assert set(ctx.keys()) == antes  # el original intacto


def test_filtro_detecta_fuga_inyectada(conn, fecha):
    """Verificación negativa: si se inyecta un campo prohibido, se detecta."""
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    ctx["composicion"][0]["rut"] = "11.111.111-1"  # fuga deliberada
    fugas = contiene_campo_prohibido(ctx)
    assert "rut" in fugas
    # pero el filtro la elimina:
    filtrado = filtrar_para_llm(ctx)
    assert contiene_campo_prohibido(filtrado) == []


def test_las_500_familias_tienen_contexto_sin_fugas(conn, fecha):
    """Contrato C2 para las 500 familias + 0 fugas al LLM."""
    fams = [r[0] for r in conn.execute(
        "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
    n = 0
    for fam in fams:
        ctx = construir_contexto(fam, conn=conn, fecha=fecha)
        assert ctx is not None
        assert contiene_campo_prohibido(filtrar_para_llm(ctx)) == []
        n += 1
    assert n == 500


# --- resiliencia a datos mal ingresados (opción A) ---------------------------

def test_contexto_resiste_tramo_mal_escrito(conn, fecha):
    """Un tramo RSH basura NO rompe el contexto y queda marcado."""
    fid = "FAM-SIM-E3-00100"
    # Ensucia el tramo en la transacción del test (sin commit -> se revierte).
    conn.execute("UPDATE familias SET tramo_rsh_corte = 'cuarenta' WHERE id_familia = ?",
                 (fid,))
    ctx = construir_contexto(fid, conn=conn, fecha=fecha)
    assert ctx is not None                      # no se cae
    assert ctx["rsh"]["tramo"] is None          # dato ilegible no se inventa
    assert any("tramo" in m for m in ctx["inconsistencias"])  # queda rastro


def test_contexto_normaliza_parentesco_mal_escrito(conn, fecha):
    fid = "FAM-SIM-E3-00100"
    conn.execute(
        "UPDATE integrantes SET parentesco = 'hijo' "
        "WHERE id_familia = ? AND parentesco = 'HIJO_HIJA'", (fid,))
    ctx = construir_contexto(fid, conn=conn, fecha=fecha)
    roles = [c["rol"] for c in ctx["composicion"]]
    assert "HIJO_HIJA" in roles                 # 'hijo' se normalizó
    assert any("parentesco" in m for m in ctx["inconsistencias"])


def test_calidad_datos_es_un_resumen(conn, fecha):
    ctx = construir_contexto("FAM-SIM-E3-00100", conn=conn, fecha=fecha)
    cd = ctx["calidad_datos"]
    assert set(cd.keys()) == {"OK", "NORMALIZADO", "SOSPECHOSO", "ILEGIBLE", "AUSENTE"}
    assert all(isinstance(v, int) for v in cd.values())
