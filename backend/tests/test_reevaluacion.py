"""Reevaluación con hechos DECLARADO por la familia (P1, plan Día 2 #4).

Verifica el flujo "ficha digital -> hechos DECLARADO -> reevaluación":

  - Sin declarados, un beneficio bloqueado SOLO por un dato ausente queda
    INDETERMINADO (comportamiento actual; regresión).
  - Con el dato declarado válido, el mismo beneficio pasa a SI pero con nivel
    PRELIMINAR (nunca CONFIRMADO), con el motivo EVIDENCIA_DECLARADA y la traza
    marcada como "declarado".
  - Un dato declarado ilegible se ignora (sigue INDETERMINADO).
  - Un declarado NO pisa un dato real presente en la base.
  - El puente `declarados_desde_propuesta` solo deja pasar campos declarables.

Caso canónico: BEN-017 (Pensión/beneficio para mujer >= 65 con hijos y
residencia acreditada). Sus únicos bloqueadores declarables son
`residencia_total_anios` (>=20) y `residencia_ultimos20_anios` (>=4); el resto
(sexo F, edad>=65, situación previsional, >=1 hijo) se construye en la familia
sintética. Así, declarar la residencia es lo único que desbloquea el SI.
"""
from __future__ import annotations

import sqlite3

import pytest

from app.engine.evaluator import Evaluator
from app.engine.facts import CAMPOS_DECLARABLES, desde_declarado
from app.engine.model import MOTIVO_EVIDENCIA_DECLARADA, Nivel, Tri
from app.genai.caracterizador import declarados_desde_propuesta

BEN = "BEN-017"
FID = "FAM-SIM-E3-REEVAL-01"
MADRE = "INT-REEVAL-01-001"
HIJO = "INT-REEVAL-01-002"


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


def _sembrar_familia(conn: sqlite3.Connection) -> None:
    """Crea una familia que cumple BEN-017 salvo por la residencia (declarable)."""
    _limpiar(conn)
    conn.execute(
        "INSERT INTO familias (id_familia, estado_rsh_corte, tramo_rsh_corte, "
        "numero_integrantes_corte, id_comuna_residencia_corte, "
        "region_codigo_residencia_corte, id_jardin) "
        "VALUES (?, 'VIGENTE', '40', '2', 'COM-001', 'REG-SIM-01', 'JAR-SIM-E3-00001')",
        (FID,))
    # Persona de referencia: mujer, >= 65 (nacida 1950) -> edad y sexo OK.
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'PERSONA_REFERENCIA', '1950-01-01', 'F', 'false')",
        (MADRE, FID))
    # Un hijo -> habilita hijos_activos (PROGENITOR_DE) >= 1.
    conn.execute(
        "INSERT INTO integrantes (id_integrante, id_familia, parentesco, "
        "fecha_nacimiento_sintetica, sexo_registral_sintetico, es_nino_jardin) "
        "VALUES (?, ?, 'HIJO_HIJA', '1990-01-01', 'M', 'false')",
        (HIJO, FID))
    conn.execute(
        "INSERT INTO relaciones_integrantes (id_relacion, id_integrante_origen, "
        "id_integrante_destino, tipo_relacion) VALUES (?, ?, ?, 'PROGENITOR_DE')",
        ("REL-REEVAL-01", MADRE, HIJO))
    # Situación previsional admitida.
    conn.execute(
        "INSERT INTO condiciones_integrante (id_condicion, id_integrante, "
        "tipo_condicion, subtipo, valor_texto, estado_dato, acreditada, "
        "vigencia_desde, vigencia_hasta) "
        "VALUES (?, ?, 'PREVISION', 'CATEGORIA', 'SIN_PENSION_PREVIA', 'OBSERVADO', "
        "'true', '2024-01-01', '2027-01-01')",
        ("CON-REEVAL-01", MADRE))


def _limpiar(conn: sqlite3.Connection) -> None:
    ints = [r[0] for r in conn.execute(
        "SELECT id_integrante FROM integrantes WHERE id_familia = ?", (FID,)).fetchall()]
    for iid in ints:
        conn.execute("DELETE FROM condiciones_integrante WHERE id_integrante = ?", (iid,))
        conn.execute("DELETE FROM relaciones_integrantes WHERE id_integrante_origen = ? "
                     "OR id_integrante_destino = ?", (iid, iid))
    conn.execute("DELETE FROM integrantes WHERE id_familia = ?", (FID,))
    conn.execute("DELETE FROM familias WHERE id_familia = ?", (FID,))


def test_sin_declarados_queda_indeterminado(conn, fecha):
    _sembrar_familia(conn)
    res = Evaluator(conn, fecha).evaluar(FID, BEN)
    assert res.resultado == Tri.INDETERMINADO
    assert "residencia_total_anios" in res.datos_faltantes
    assert "residencia_ultimos20_anios" in res.datos_faltantes


def test_declarar_residencia_desbloquea_si_preliminar(conn, fecha):
    _sembrar_familia(conn)
    declarados = {"integrante": {MADRE: {
        "residencia_total_anios": 30,
        "residencia_ultimos20_anios": 10,
    }}}
    res = Evaluator(conn, fecha).evaluar(FID, BEN, declarados)
    assert res.resultado == Tri.SI
    # Un dato declarado NUNCA puede dar CONFIRMADO.
    assert res.nivel == Nivel.PRELIMINAR
    assert MOTIVO_EVIDENCIA_DECLARADA in res.motivos
    # La traza deja rastro auditable del dato declarado.
    notas = [t.nota for t in res.traza if t.resultado == Tri.SI]
    assert "declarado" in notas


def test_declarado_ilegible_se_ignora(conn, fecha):
    _sembrar_familia(conn)
    declarados = {"integrante": {MADRE: {
        "residencia_total_anios": "no-sé",      # ilegible -> se ignora
        "residencia_ultimos20_anios": 10,
    }}}
    res = Evaluator(conn, fecha).evaluar(FID, BEN, declarados)
    assert res.resultado == Tri.INDETERMINADO
    assert "residencia_total_anios" in res.datos_faltantes
    assert "residencia_ultimos20_anios" not in res.datos_faltantes


def test_valor_insuficiente_no_desbloquea(conn, fecha):
    """Un valor declarado válido pero bajo el umbral da NO, no SI (no es magia)."""
    _sembrar_familia(conn)
    declarados = {"integrante": {MADRE: {
        "residencia_total_anios": 2,            # < 20 requerido
        "residencia_ultimos20_anios": 1,        # < 4 requerido
    }}}
    res = Evaluator(conn, fecha).evaluar(FID, BEN, declarados)
    assert res.resultado == Tri.NO


def test_declarado_no_pisa_dato_real(conn, fecha):
    """Si la base ya trae el dato, el declarado no lo sobreescribe."""
    _sembrar_familia(conn)
    # situacion_previsional ya está en la base como SIN_PENSION_PREVIA; intentar
    # declararla a un valor fuera de dominio no debe cambiar la evaluación.
    declarados = {
        "integrante": {MADRE: {
            "residencia_total_anios": 30,
            "residencia_ultimos20_anios": 10,
            "situacion_previsional": "VALOR_INVENTADO",  # no declarable -> ignorado
        }}
    }
    res = Evaluator(conn, fecha).evaluar(FID, BEN, declarados)
    assert res.resultado == Tri.SI  # el dato real de la base manda


# --- helper desde_declarado y puente del LLM ---------------------------------

def test_desde_declarado_tipos():
    assert desde_declarado("residencia_total_anios", "30").valor == 30
    # Un valor no numérico para un campo "num" es ilegible -> None.
    assert desde_declarado("residencia_total_anios", "no") is None
    assert desde_declarado("parto_red_publica", "si").valor is True
    assert desde_declarado("parto_red_publica", "no").valor is False
    assert desde_declarado("campo_inexistente", 5) is None
    h = desde_declarado("semanas_gestacion", 30)
    assert h.acreditada is False and h.estado_dato == "DECLARADO"


def test_declarables_son_subconjunto_de_faltantes():
    from app.engine.facts import CAMPOS_FALTANTES
    # Además de los faltantes, tres respaldos de hogar que solo se usan si la base
    # no trae el dato (o, para gestación, porque el dataset no la trae nunca).
    respaldos = {"gestacion_declarada", "cobertura_incompatible", "tramo_rsh"}
    assert set(CAMPOS_DECLARABLES) <= set(CAMPOS_FALTANTES) | respaldos


def test_puente_declarados_desde_propuesta():
    prop = {"hechos_declarados": {
        "hogar": {"dias_desde_evento": 10, "campo_raro": 5},
        "integrante": {"INT-X": {"semanas_gestacion": 30, "nombre": "fuga"}},
    }}
    out = declarados_desde_propuesta(prop)
    assert out == {
        "hogar": {"dias_desde_evento": 10},
        "integrante": {"INT-X": {"semanas_gestacion": 30}},
    }


def test_puente_sin_hechos_devuelve_vacio():
    assert declarados_desde_propuesta({"senales_detectadas": ["x"]}) == {}
    assert declarados_desde_propuesta({}) == {}
