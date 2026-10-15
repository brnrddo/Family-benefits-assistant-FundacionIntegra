"""Puente pantalla -> motor de la propuesta ``antecedentes`` (B2).

Verifica las piezas puras que traducen el cuerpo de la pantalla a los hechos
que el motor sabe usar:

- la fecha del último control de salud se convierte a ``dias_desde_control``
  (días, nunca negativo; fecha ilegible -> no se inyecta);
- el dato se asigna al niño o niña MÁS JOVEN de la familia (menor de 18);
- ningún otro campo de la pantalla (p. ej. ``has_rsh``, ``household_pregnancy``)
  llega al motor por esta vía.
"""
from __future__ import annotations

import sqlite3

from app.api.antecedentes_motor import (
    dias_desde_fecha,
    declarados_para_motor,
    nino_mas_joven,
)

FID = "FAM-SIM-E3-BRIDGE-01"
MADRE = "INT-BRIDGE-01-001"
HIJO_MAYOR = "INT-BRIDGE-01-002"
HIJO_MENOR = "INT-BRIDGE-01-003"
FECHA = "2026-10-13"


def _sembrar(conn: sqlite3.Connection) -> None:
    _limpiar(conn)
    conn.execute(
        "INSERT INTO familias (id_familia, estado_rsh_corte, tramo_rsh_corte, "
        "numero_integrantes_corte, id_comuna_residencia_corte, "
        "region_codigo_residencia_corte, id_jardin) "
        "VALUES (?, 'VIGENTE', '40', '3', 'COM-001', 'REG-SIM-01', 'JAR-SIM-E3-00001')",
        (FID,))
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'PERSONA_REFERENCIA', '1990-01-01', 'F', 'false')",
        (MADRE, FID))
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'HIJO_HIJA', '2018-01-01', 'M', 'false')",
        (HIJO_MAYOR, FID))
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'HIJO_HIJA', '2023-01-01', 'M', 'true')",
        (HIJO_MENOR, FID))
    conn.commit()


def _limpiar(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM integrantes WHERE id_familia = ?", (FID,))
    conn.execute("DELETE FROM familias WHERE id_familia = ?", (FID,))
    conn.commit()


def test_dias_desde_fecha_basico():
    assert dias_desde_fecha("2026-10-01", FECHA) == 12
    # Fecha de control en el futuro respecto de la evaluación: 0, nunca negativo.
    assert dias_desde_fecha("2026-12-01", FECHA) == 0
    # Mismo día: 0.
    assert dias_desde_fecha(FECHA, FECHA) == 0


def test_dias_desde_fecha_ilegible():
    assert dias_desde_fecha("no-es-fecha", FECHA) is None
    assert dias_desde_fecha("2026-13-40", FECHA) is None
    assert dias_desde_fecha("", FECHA) is None


def test_nino_mas_joven_elige_el_menor(conn):
    _sembrar(conn)
    try:
        assert nino_mas_joven(conn, FID, FECHA) == HIJO_MENOR
    finally:
        _limpiar(conn)


def test_nino_mas_joven_sin_menores_es_none(conn):
    _limpiar(conn)
    conn.execute(
        "INSERT INTO familias (id_familia, estado_rsh_corte, tramo_rsh_corte, "
        "numero_integrantes_corte, id_comuna_residencia_corte, "
        "region_codigo_residencia_corte, id_jardin) "
        "VALUES (?, 'VIGENTE', '40', '1', 'COM-001', 'REG-SIM-01', 'JAR-SIM-E3-00001')",
        (FID,))
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'PERSONA_REFERENCIA', '1980-01-01', 'F', 'false')",
        (MADRE, FID))
    conn.commit()
    try:
        assert nino_mas_joven(conn, FID, FECHA) is None
    finally:
        _limpiar(conn)


def test_declarados_para_motor_mapea_solo_fecha_control(conn):
    _sembrar(conn)
    try:
        campos = {
            "last_child_health_control_date": "2026-10-01",
            "has_rsh": True,                 # no declarable al motor -> se ignora
            "household_pregnancy": True,     # bool; el motor pide semanas -> se ignora
        }
        out = declarados_para_motor(conn, FID, campos, FECHA)
        assert out == {"integrante": {HIJO_MENOR: {"dias_desde_control": 12}}}
    finally:
        _limpiar(conn)


def test_declarados_para_motor_sin_fecha_es_vacio(conn):
    _sembrar(conn)
    try:
        assert declarados_para_motor(conn, FID, {"has_rsh": True}, FECHA) == {}
        # Fecha ilegible tampoco inyecta nada.
        assert declarados_para_motor(
            conn, FID, {"last_child_health_control_date": "ayer"}, FECHA) == {}
    finally:
        _limpiar(conn)
