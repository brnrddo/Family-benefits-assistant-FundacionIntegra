"""Objeto `contexto_familia` — contrato C2 (spec §2.7.2).

Es lo que entrega el Rol 1 al Rol 2 (plazo spec: Día 2, 12:00). Describe el
contexto humano de la familia para decidir tono, formato y urgencia, SIN
decidir elegibilidad y SIN datos prohibidos.

Forma exacta (§2.7.2):
    {
      "id_familia", "fuente",
      "composicion": [{"rol", "edad"}],
      "rsh": {"tiene", "tramo"},
      "ingreso_per_capita_rango",
      "senales_vulnerabilidad": {...},
      "senales_urgencia": {...},
      "posible_discapacidad_nino",
      "formato_preferido", "idioma_mensaje",
      "inconsistencias": [...],
      "no_informado": [...]
    }

El filtro hacia el LLM vive en `context_filter.py` (§2.7.3), NO aquí: este
objeto contiene más de lo que ve el LLM (p. ej. señales de vulnerabilidad),
porque la tía sí puede verlas en su dispositivo.
"""
from __future__ import annotations

import sqlite3

from ..config import DB_PATH, FECHA_EVALUACION
from ..profile.builder import ProfileBuilder
from .ficha_sintetica import NO_INFORMADO, FichaSinteticaBuilder
from .sanitizer import (Calidad, ReporteCalidad, Saneado, sanear_ingreso,
                        sanear_parentesco, sanear_tramo_rsh)

# parentesco del dataset -> rol legible para el contexto (§2.7.2 usa roles).
ROL_POR_PARENTESCO = {
    "PERSONA_REFERENCIA": "ADULTA_REFERENCIA",
    "PAREJA": "PAREJA",
    "HIJO_HIJA": "HIJO_HIJA",
    "OTRO_PARIENTE": "OTRO_PARIENTE",
}


def _rango_ingreso_pc(ingreso_pc) -> str:
    """Rango grueso de ingreso per cápita (no el monto exacto, §2.7.3)."""
    if ingreso_pc in (None, "", NO_INFORMADO):
        return NO_INFORMADO
    try:
        v = float(ingreso_pc)
    except (ValueError, TypeError):
        return NO_INFORMADO
    if v < 110_000:
        return "MENOS_110K"
    if v < 250_000:
        return "ENTRE_110K_250K"
    if v < 400_000:
        return "ENTRE_250K_400K"
    return "MAS_400K"


def _conn(db_path=None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or DB_PATH))
    c.row_factory = sqlite3.Row
    return c


class ContextoBuilder:
    def __init__(self, conn: sqlite3.Connection, fecha: str = FECHA_EVALUACION):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha
        self.profile = ProfileBuilder(conn, fecha)
        self.ficha_builder = FichaSinteticaBuilder(conn, fecha)

    def build(self, id_familia: str) -> dict | None:
        perfil = self.profile.build(id_familia, incluir_recomendacion=False)
        if perfil is None:
            return None
        ficha = self.ficha_builder.build(id_familia)

        comp = perfil["composicion"]
        rsh = perfil["rsh"]

        # Reporte de calidad: acumula el saneo de cada dato dudoso para poblar
        # `inconsistencias` (resiliencia a datos mal ingresados, opción A).
        reporte = ReporteCalidad()

        # --- composición: roles + edades (sin nombres ni RUT) ----------------
        # Cada parentesco y edad se sanea; un dato ilegible NO rompe la familia,
        # degrada el campo y deja rastro en inconsistencias.
        composicion = []
        for i in comp["integrantes"]:
            s_par = reporte.registrar(sanear_parentesco(i["parentesco"]))
            rol = (ROL_POR_PARENTESCO.get(s_par.valor, "OTRO_PARIENTE")
                   if s_par.utilizable else "DESCONOCIDO")
            # La edad ya viene derivada por el perfil; si el perfil no pudo
            # calcularla (None) puede ser por fecha mal escrita: se marca.
            edad = i["edad"]
            if edad is None:
                reporte.registrar(Saneado(
                    "edad", None, Calidad.ILEGIBLE, None,
                    f"integrante {i.get('id_integrante','?')}: edad no derivable "
                    "(fecha de nacimiento ausente o mal escrita)"))
            composicion.append({"rol": rol, "edad": edad})

        # --- rsh --------------------------------------------------------------
        s_tramo = reporte.registrar(sanear_tramo_rsh(rsh["tramo_rsh"])
                                    if rsh["rsh_conocido"] else
                                    Saneado("tramo_rsh", None, Calidad.AUSENTE, None))
        tiene_rsh = rsh["estado_rsh"] == "VIGENTE" and rsh["rsh_conocido"]
        rsh_ctx = {
            "tiene": tiene_rsh,
            "tramo": s_tramo.valor if s_tramo.utilizable else None,
        }

        # --- rango de ingreso -------------------------------------------------
        s_ingreso = reporte.registrar(sanear_ingreso(ficha["ingreso_per_capita"]))
        ingreso_rango = (_rango_ingreso_pc(s_ingreso.valor)
                         if s_ingreso.utilizable else NO_INFORMADO)

        # --- señales de vulnerabilidad (solo lo derivable) -------------------
        # Las no derivables del dataset NO se inventan: quedan como NO_INFORMADO
        # y además se listan en `no_informado`.
        senales_vulnerabilidad = {
            "subsistema_ssyo": ficha["subsistema_ssyo"],
            "fonasa_tramo": NO_INFORMADO,       # previsión de salud no está en E-3
            "puntaje_cse": NO_INFORMADO,
            "jefa_hogar_sernameg": NO_INFORMADO,
        }

        # --- señales de urgencia (solo lo derivable) -------------------------
        senales_urgencia = {
            "vivienda_precaria": NO_INFORMADO,   # vivienda no está en E-3
            "inseguridad_alimentaria": self._indice_inseguridad(id_familia),
            "evento_emergencia": self._tiene_evento_emergencia(id_familia),
        }

        # --- inconsistencias: lo que NO estaba limpio (resiliencia opción A) --
        # Datos mal escritos que se normalizaron, quedaron fuera de rango o
        # fueron ilegibles. La tía los ve como "revisar/preguntar"; nunca se
        # inventa un valor. Se combina con el placeholder de FICHA_DIGITAL (S2).
        inconsistencias = reporte.inconsistencias()

        # --- no_informado: campos de la ficha que el dataset no permite ------
        no_informado = sorted(
            k for k, v in ficha.items()
            if v == NO_INFORMADO
        )

        return {
            "id_familia": id_familia,
            "fuente": ficha["fuente"],
            "composicion": composicion,
            "rsh": rsh_ctx,
            "ingreso_per_capita_rango": ingreso_rango,
            "senales_vulnerabilidad": senales_vulnerabilidad,
            "senales_urgencia": senales_urgencia,
            "posible_discapacidad_nino": ficha["posible_discapacidad_nino"],
            "formato_preferido": "TEXTO",   # escolaridad del apoderado no está en E-3
            "idioma_mensaje": "es",         # nacionalidad no va al motor/LLM; default es
            "inconsistencias": inconsistencias,
            "no_informado": no_informado,
            "calidad_datos": reporte.resumen(),
        }

    def _indice_inseguridad(self, id_familia: str):
        from ..engine.facts import Repo
        rows = self.conn.execute(
            "SELECT valor_numero, vigencia_desde, vigencia_hasta FROM antecedentes_familia "
            "WHERE id_familia = ? AND tipo_antecedente = 'INSEGURIDAD_ALIMENTARIA' "
            "AND subtipo = 'INDICE'", (id_familia,)
        ).fetchall()
        for r in rows:
            if Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                v = r["valor_numero"]
                try:
                    return float(v) if v not in (None, "") else None
                except (ValueError, TypeError):
                    return None
        return None

    def _tiene_evento_emergencia(self, id_familia: str) -> bool:
        from ..engine.facts import Repo
        rows = self.conn.execute(
            "SELECT vigencia_desde, vigencia_hasta FROM antecedentes_familia "
            "WHERE id_familia = ? AND tipo_antecedente = 'EVENTO_EMERGENCIA'",
            (id_familia,)
        ).fetchall()
        return any(
            Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha) for r in rows)


def construir_contexto(id_familia: str, conn=None, fecha=FECHA_EVALUACION) -> dict | None:
    propia = conn is None
    conn = conn or _conn()
    try:
        return ContextoBuilder(conn, fecha).build(id_familia)
    finally:
        if propia:
            conn.close()
