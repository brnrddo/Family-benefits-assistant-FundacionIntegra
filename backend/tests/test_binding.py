"""Test de binding "mismo niño o niña" (spec §6.7).

Verifica que las reglas de un mismo binding deben cumplirse por la MISMA
entidad. Caso canónico: BEN-006 (Subsidio discapacidad < 18) exige que el
mismo causante sea < 18 Y tenga discapacidad SEVERA vigente.

- Positivo: un niño < 18 con discapacidad severa -> SI.
- Negativo: la edad la cumple un niño y la discapacidad un adulto (dos entidades
  distintas) -> NO debe dar SI (ningún candidato cumple ambas).

Se construye una familia sintética en una copia de la DB para controlar el caso.
"""
from __future__ import annotations

import sqlite3

import pytest

from app.engine.evaluator import Evaluator
from app.engine.model import Tri


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


def _nueva_familia(conn: sqlite3.Connection, fid: str, tramo: str = "40"):
    conn.execute(
        "INSERT INTO familias (id_familia, estado_rsh_corte, tramo_rsh_corte, "
        "numero_integrantes_corte, id_comuna_residencia_corte, region_codigo_residencia_corte, id_jardin) "
        "VALUES (?, 'VIGENTE', ?, '2', 'COM-001', 'REG-SIM-01', 'JAR-SIM-E3-00001')",
        (fid, tramo))


def _nuevo_integrante(conn, iid, fid, parentesco, fecha_nac):
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, ?, ?, 'F', 'false')",
        (iid, fid, parentesco, fecha_nac))


def _discapacidad_severa(conn, iid, cid):
    conn.execute(
        "INSERT INTO condiciones_integrante (id_condicion, id_integrante, tipo_condicion, "
        "subtipo, valor_texto, estado_dato, acreditada, vigencia_desde, vigencia_hasta) "
        "VALUES (?, ?, 'DISCAPACIDAD', 'SEVERIDAD', 'SEVERA', 'OBSERVADO', 'true', '2025-01-01', '2027-01-01')",
        (cid, iid))


def _limpiar(conn, fid: str):
    """Borra una familia de prueba y sus dependencias (idempotencia).

    Evita colisiones de PK si el id quedara de una corrida previa. Opera en la
    transacción del test (sin commit), así no toca la DB de sesión.
    """
    ints = [r[0] for r in conn.execute(
        "SELECT id_integrante FROM integrantes WHERE id_familia = ?", (fid,)).fetchall()]
    for iid in ints:
        conn.execute("DELETE FROM condiciones_integrante WHERE id_integrante = ?", (iid,))
    conn.execute("DELETE FROM integrantes WHERE id_familia = ?", (fid,))
    conn.execute("DELETE FROM familias WHERE id_familia = ?", (fid,))


def test_binding_mismo_nino_positivo(conn, fecha):
    """Un mismo niño < 18 con discapacidad severa -> BEN-006 SI."""
    fid = "FAM-TEST-BINDING-POS"
    _limpiar(conn, fid)
    _nueva_familia(conn, fid)
    _nuevo_integrante(conn, "PER-TB-POS-1", fid, "PERSONA_REFERENCIA", "1990-01-01")  # adulto
    _nuevo_integrante(conn, "PER-TB-POS-2", fid, "HIJO_HIJA", "2015-01-01")           # niño < 18
    _discapacidad_severa(conn, "PER-TB-POS-2", "COND-TB-POS-1")  # el niño tiene discapacidad
    # Sin commit: la misma conexión ve sus inserts, pero al cerrarse se
    # descartan (no contaminan la DB de sesión compartida por otros tests).

    r = Evaluator(conn, fecha).evaluar(fid, "BEN-006")
    assert r.resultado == Tri.SI
    assert r.entidad_ganadora.get("CAUSANTE_1") == "PER-TB-POS-2"


def test_binding_mismo_nino_negativo(conn, fecha):
    """La edad la cumple un niño y la discapacidad un adulto -> NO debe dar SI.

    Ninguna entidad cumple AMBAS condiciones del binding CAUSANTE_1.
    """
    fid = "FAM-TEST-BINDING-NEG"
    _limpiar(conn, fid)
    _nueva_familia(conn, fid)
    # Niño < 18 SIN discapacidad.
    _nuevo_integrante(conn, "PER-TB-NEG-1", fid, "HIJO_HIJA", "2015-01-01")
    # Adulto CON discapacidad severa (no cumple edad < 18).
    _nuevo_integrante(conn, "PER-TB-NEG-2", fid, "PERSONA_REFERENCIA", "1980-01-01")
    _discapacidad_severa(conn, "PER-TB-NEG-2", "COND-TB-NEG-1")
    # Sin commit (ver nota en el caso positivo): aísla la familia de prueba.

    r = Evaluator(conn, fecha).evaluar(fid, "BEN-006")
    # El niño cumple edad pero le falta discapacidad (IND); el adulto no es
    # candidato CAUSANTE (>=18). En ningún caso debe ser SI.
    assert r.resultado != Tri.SI


# --- REF_EQ: vínculo entre bindings (BEN-016 Asignación Familiar) ------------

def test_ref_eq_ben016_vincula_causante_con_beneficiario(conn, fecha):
    """BEN-016 exige que el CAUSANTE sea carga acreditada del BENEFICIARIO.

    Con REF_EQ resuelto, una familia con esa relación acreditada debe poder dar
    SI y la entidad ganadora debe enlazar ambos bindings.
    """
    r = Evaluator(conn, fecha).evaluar("FAM-SIM-E3-00001", "BEN-016")
    assert r.resultado == Tri.SI
    assert "BENEFICIARIO_1" in r.entidad_ganadora
    assert "CAUSANTE_1" in r.entidad_ganadora
    # la traza del REF_EQ debe quedar como CUMPLE (SI)
    ref = [t for t in r.traza if t.operador == "REF_EQ"]
    assert ref and ref[0].resultado == Tri.SI


def test_ref_eq_sin_relacion_no_da_si(conn, fecha):
    """Si se borra la relación CARGA_DE, BEN-016 no debe dar SI por REF_EQ."""
    fid = "FAM-SIM-E3-00002"
    conn.execute(
        "DELETE FROM relaciones_integrantes "
        "WHERE id_familia = ? AND tipo_relacion = 'CARGA_DE'", (fid,))
    # sin commit: la conexión del test ve el borrado; se revierte al cerrar.
    r = Evaluator(conn, fecha).evaluar(fid, "BEN-016")
    assert r.resultado != Tri.SI


# --- regresión: traza conservada cuando un binding EXISTS no tiene ganador ---

def test_binding_exists_sin_ganador_conserva_traza(conn, fecha):
    """Si ningún candidato cumple un binding EXISTS, el resultado es NO/IND pero
    la traza NO debe quedar vacía: debe mostrar las reglas del candidato
    evaluado (explicabilidad). Bug detectado al pasar el dataset completo.

    Caso: familia cuyo único estudiante candidato es un niño de jardín menor
    que la edad mínima de BEN-013 → NO, pero con traza de las reglas ESTUDIANTE.
    """
    # Familia con un hijo pequeño matriculado y SSyO activo (grupo con binding
    # HOGAR + ESTUDIANTE_1). Buscamos una donde BEN-013 dé NO por edad.
    r = None
    for n in range(1, 60):
        fam = f"FAM-SIM-E3-{n:05d}"
        res = Evaluator(conn, fecha).evaluar(fam, "BEN-013")
        if res.resultado == Tri.NO and any(
                t.binding_grupo.startswith("ESTUDIANTE") for t in res.traza):
            r = res
            break
    assert r is not None, "no se halló una familia BEN-013=NO con binding estudiante"
    # La traza debe incluir reglas del binding ESTUDIANTE (no solo el HOGAR).
    bindings_en_traza = {t.binding_grupo for t in r.traza}
    assert any(b.startswith("ESTUDIANTE") for b in bindings_en_traza), (
        f"traza sin binding estudiante: {bindings_en_traza}")
    # Y debe haber más de una regla (no quedó truncada en vacío).
    assert len(r.traza) >= 2
