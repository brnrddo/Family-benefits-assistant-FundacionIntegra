"""Ficha sintética por familia (M3b, spec §2.7).

La Ficha de Inscripción y Matrícula de Integra es un formato vacío: el dataset
E-3 no trae fichas llenas. Para la demo se genera una ficha sintética por
familia **derivada del dataset**. Los campos que la ficha pide pero el dataset
no permite derivar quedan como ``NO_INFORMADO`` y nunca se inventan (§2.7).

Esta ficha es:
  1. fuente de hechos DECLARADO para el motor (no la consume este módulo),
  2. contexto para la tía/IA (vía `contexto_familia`),
  3. plantilla del cuestionario de familia nueva (S2).

El mapeo campo→dato sigue §2.7.1. Donde §2.7.1 dice "no existe en E-3", el
campo queda ``NO_INFORMADO``.
"""
from __future__ import annotations

import sqlite3

from ..config import DB_PATH, FECHA_EVALUACION
from ..profile.builder import ProfileBuilder

# Marcador explícito para datos que la ficha pide pero el dataset no trae.
NO_INFORMADO = "NO_INFORMADO"

# Tramos de edad de hermanos que pide la ficha (§2.7.1).
#   < 6, 6–14, 15–18
def _tramo_hermanos(edad: int | None) -> str | None:
    if edad is None:
        return None
    if edad < 6:
        return "menor_6"
    if edad <= 14:
        return "entre_6_14"
    if edad <= 18:
        return "entre_15_18"
    return None


def _conn(db_path=None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or DB_PATH))
    c.row_factory = sqlite3.Row
    return c


class FichaSinteticaBuilder:
    """Deriva la ficha de matrícula sintética a partir del perfil consolidado."""

    def __init__(self, conn: sqlite3.Connection, fecha: str = FECHA_EVALUACION):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha
        self.profile = ProfileBuilder(conn, fecha)

    def build(self, id_familia: str) -> dict | None:
        perfil = self.profile.build(id_familia, incluir_recomendacion=False)
        if perfil is None:
            return None

        comp = perfil["composicion"]
        rsh = perfil["rsh"]
        ant = perfil["antecedentes"]

        # --- edad del niño/a de jardín (si hay varios, el primero) -----------
        ninos = comp["ninos_jardin"]
        edad_nino = ninos[0]["edad"] if ninos else NO_INFORMADO

        # --- hermanos por tramo de edad (hijos/as, excluye adultos) ----------
        hermanos = {"menor_6": 0, "entre_6_14": 0, "entre_15_18": 0}
        for i in comp["integrantes"]:
            if i["parentesco"] != "HIJO_HIJA":
                continue
            tramo = _tramo_hermanos(i["edad"])
            if tramo:
                hermanos[tramo] += 1

        # --- RSH --------------------------------------------------------------
        tiene_rsh = rsh["estado_rsh"] == "VIGENTE" and rsh["rsh_conocido"]
        tramo_rsh = rsh["tramo_rsh"] if rsh["rsh_conocido"] else NO_INFORMADO

        # --- ingreso per cápita (derivado) -----------------------------------
        ingreso = ant.get("ingreso_hogar")
        n = _num(perfil["composicion"]["numero_integrantes"])
        ingreso_pc = int(ingreso / n) if (ingreso not in (None, "") and n) else NO_INFORMADO

        # --- señales derivables de condiciones/antecedentes ------------------
        posible_discapacidad = any(
            c["tipo"] == "DISCAPACIDAD" for c in ant["condiciones"])
        subsistema_ssyo = self._eav_hogar_presente(
            id_familia, "SUBSISTEMA_SSYO", "PARTICIPACION", valor_esperado="ACTIVA")
        control_salud = any(
            c["tipo"] == "CONTROL_SALUD" for c in ant["condiciones"])

        return {
            "id_familia": id_familia,
            "fuente": "FICHA_SINTETICA",
            # Campos derivables del dataset:
            "edad_nino_jardin": edad_nino,
            "hermanos_por_tramo": hermanos,
            "tiene_rsh": tiene_rsh,
            "tramo_rsh": tramo_rsh,
            "ingreso_per_capita": ingreso_pc,
            "subsistema_ssyo": subsistema_ssyo,
            "control_salud_infantil": control_salud,
            "posible_discapacidad_nino": posible_discapacidad,
            # Campos de la ficha que el dataset NO trae (§2.7.1) -> NO_INFORMADO:
            "chile_crece_contigo": NO_INFORMADO,
            "prevision_salud": NO_INFORMADO,
            "puntaje_cse": NO_INFORMADO,
            "vivienda": NO_INFORMADO,
            "jefa_hogar_sernameg": NO_INFORMADO,
            "escolaridad_apoderado": NO_INFORMADO,
            "nacionalidad": NO_INFORMADO,
            "persona_cuidado_dia": NO_INFORMADO,
            "embarazo": NO_INFORMADO,
        }

    def _eav_hogar_presente(self, id_familia, tipo, subtipo, valor_esperado=None):
        rows = self.conn.execute(
            "SELECT valor_texto, vigencia_desde, vigencia_hasta FROM antecedentes_familia "
            "WHERE id_familia = ? AND tipo_antecedente = ? AND subtipo = ?",
            (id_familia, tipo, subtipo),
        ).fetchall()
        from ..engine.facts import Repo
        for r in rows:
            if not Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                continue
            if valor_esperado is None:
                return True
            return str(r["valor_texto"]).upper() == valor_esperado.upper()
        return False


def _num(v):
    if v in (None, ""):
        return None
    try:
        return int(v) if "." not in str(v) else float(v)
    except (ValueError, TypeError):
        return None


def construir_ficha(id_familia: str, conn=None, fecha=FECHA_EVALUACION) -> dict | None:
    propia = conn is None
    conn = conn or _conn()
    try:
        return FichaSinteticaBuilder(conn, fecha).build(id_familia)
    finally:
        if propia:
            conn.close()
