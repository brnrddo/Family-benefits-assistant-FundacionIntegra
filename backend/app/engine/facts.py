"""Resolución de hechos: mapa ``campo_dato -> origen`` (M2, enfoque SQL directo).

Dado un ``campo_dato`` lógico que piden las reglas, resuelve su valor para una
entidad (hogar o integrante) a la fecha de evaluación, consultando SQLite.

Tres categorías de campo:
  1. DIRECTO   -> columna de `familias` / `integrantes`.
  2. EAV       -> fila de `condiciones_integrante` / `antecedentes_familia`
                  filtrando por tipo/subtipo y vigencia.
  3. DERIVADO  -> cálculo simple sobre uno o más hechos (edad, % agua, ingreso pc).
  4. FALTANTE  -> el dataset no trae el dato -> Hecho(presente=False) -> INDETERMINADO.

La vigencia es semiabierta: vigente si ``vigencia_desde <= fecha < vigencia_hasta``
(``vigencia_hasta`` NULL = abierto).
"""
from __future__ import annotations

import datetime as dt
import sqlite3

from .model import Hecho

# EAV de condiciones por integrante:  campo_dato -> (tipo, subtipo, columna_valor)
EAV_INTEGRANTE = {
    "asistencia_pct":               ("ASISTENCIA", "PORCENTAJE", "valor_numero"),
    "control_infantil_red_publica": ("CONTROL_SALUD", "INFANTIL_RED_PUBLICA", "valor_booleano"),
    "percentil_desempeno":          ("DESEMPENO", "PERCENTIL", "valor_numero"),
    "discapacidad_severidad":       ("DISCAPACIDAD", "SEVERIDAD", "valor_texto"),
    "establecimiento_adscrito_pae": ("MATRICULA", "ADSCRITO_PAE", "valor_booleano"),
    "matricula_vigencia":           ("MATRICULA", "ESTADO", "valor_texto"),
    "nivel":                        ("MATRICULA", "NIVEL", "valor_texto"),
    "tipo_establecimiento":         ("MATRICULA", "TIPO_ESTABLECIMIENTO", "valor_texto"),
    "situacion_previsional":        ("PREVISION", "CATEGORIA", "valor_texto"),
    "ingreso_bruto":                ("PREVISION", "INGRESO_BRUTO", "valor_numero"),
    "distancia_terapia_km":         ("TERAPIA", "DISTANCIA_KM", "valor_numero"),
    "terapia_vigencia":             ("TERAPIA", "ESTADO", "valor_texto"),
    # discapacidad_vigencia: se trata como ACTIVE_ON_DATE sobre DISCAPACIDAD.
    "discapacidad_vigencia":        ("DISCAPACIDAD", "SEVERIDAD", "valor_texto"),
}

# EAV de antecedentes por hogar
EAV_HOGAR = {
    "acompanamiento_aceptado":  ("ACOMPANAMIENTO", "ACEPTADO", "valor_booleano"),
    "cobertura_incompatible":   ("COBERTURA_INCOMPATIBLE", "ESTADO", "valor_booleano"),
    "tipo_evento":              ("EVENTO_EMERGENCIA", "TIPO", "valor_texto"),
    "informe_derivacion_vigente": ("INFORME_DERIVACION", "VIGENTE", "valor_booleano"),
    "indice_inseguridad":       ("INSEGURIDAD_ALIMENTARIA", "INDICE", "valor_numero"),
    "comuna_residencia":        ("RESIDENCIA", "COMUNA", "valor_texto"),
    "subsistema_ssyo_vigencia": ("SUBSISTEMA_SSYO", "PARTICIPACION", "valor_texto"),
}

# Campos que las reglas piden pero el dataset NO trae -> siempre INDETERMINADO.
# (Documentado en README como supuesto; se convierten en preguntas en capas superiores.)
CAMPOS_FALTANTES = {
    "antecedente_edad_vigente",
    "semanas_gestacion",
    "parto_red_publica",
    "control_prenatal_red_publica",
    "dias_desde_control",
    "dias_desde_evento",
    "residencia_total_anios",
    "residencia_ultimos20_anios",
}

# --- Reevaluación con hechos DECLARADO por la familia (P1) --------------------
# La tía (o el LLM, vía caracterizador) puede DECLARAR un dato que el dataset no
# trae. Un hecho declarado nunca viene acreditado -> el beneficio puede dar SI
# pero como PRELIMINAR (nunca CONFIRMADO). Solo se permiten los campos que hoy
# son faltantes/ausentes o que la base puede no traer; un declarado NUNCA pisa
# un dato real de la base (el resolver consulta la base primero).
#
# De hogar: ``gestacion_declarada`` (habilita el candidato GESTANTE; ``False``
# deja el beneficio de embarazo en NO), ``cobertura_incompatible`` (respaldo si
# la base no trae el antecedente) y ``tramo_rsh`` (respaldo si la familia no
# trae ``tramo_rsh_corte``).
#
# Tipo esperado de cada campo declarable, para validar/convertir el valor:
#   "num"  -> entero/decimal (se rechaza lo no numérico)
#   "bool" -> booleano (acepta true/false, "si"/"no", 1/0)
CAMPOS_DECLARABLES = {
    "gestacion_declarada": "bool",
    "cobertura_incompatible": "bool",
    "tramo_rsh": "num",
    "semanas_gestacion": "num",
    "parto_red_publica": "bool",
    "control_prenatal_red_publica": "bool",
    "dias_desde_control": "num",
    "dias_desde_evento": "num",
    "residencia_total_anios": "num",
    "residencia_ultimos20_anios": "num",
    "antecedente_edad_vigente": "bool",
}

_VERDADEROS = {"true", "1", "si", "sí", "verdadero", "yes"}
_FALSOS = {"false", "0", "no", "falso"}


def _coerce_declarado(campo: str, valor):
    """Convierte/valida un valor declarado al tipo del campo.

    Devuelve el valor convertido, o ``None`` si es ilegible (se ignora y el
    campo sigue INDETERMINADO). No inventa valores.
    """
    tipo = CAMPOS_DECLARABLES.get(campo)
    if tipo is None or valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if tipo == "num":
        try:
            s = str(valor).strip().replace(" ", "")
            return int(s) if "." not in s else float(s)
        except (ValueError, TypeError):
            return None
    if tipo == "bool":
        if isinstance(valor, bool):
            return valor
        s = str(valor).strip().lower()
        if s in _VERDADEROS:
            return True
        if s in _FALSOS:
            return False
        return None
    return None


def desde_declarado(campo: str, valor, id_origen: str | None = None) -> Hecho | None:
    """Construye un Hecho DECLARADO (no acreditado) a partir de un valor crudo.

    Devuelve ``None`` si el campo no es declarable o el valor es ilegible; en ese
    caso el resolver sigue su curso normal (-> INDETERMINADO).
    """
    conv = _coerce_declarado(campo, valor)
    if conv is None:
        return None
    return Hecho(campo=campo, valor=conv, presente=True, acreditada=False,
                 estado_dato="DECLARADO", id_origen=id_origen)

# Documento acreditante por campo (alimenta el checklist de M3/M5; aquí solo se define).
DOCUMENTO_POR_CAMPO = {
    "tramo_rsh": "Registro Social de Hogares al día",
    "discapacidad_severidad": "Credencial de discapacidad / certificado",
    "discapacidad_vigencia": "Credencial de discapacidad vigente",
    "matricula_vigencia": "Certificado de matrícula",
    "ingreso_bruto": "Liquidación de sueldo o certificado de ingresos",
    "situacion_previsional": "Certificado previsional",
    "gasto_agua_pct_ingreso": "Boleta de agua",
    "mora_dias": "Boleta de agua al día",
    "terapia_vigencia": "Documento de la terapia (vigente)",
    "informe_derivacion_vigente": "Informe de derivación",
}


class Repo:
    """Acceso de solo lectura a la DB para resolver hechos."""

    def __init__(self, conn: sqlite3.Connection, fecha: str):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha

    # --- helpers de vigencia ---------------------------------------------------
    @staticmethod
    def _vig(desde, hasta, fecha) -> bool:
        if desde is not None and not (desde <= fecha):
            return False
        if hasta is not None and not (fecha < hasta):
            return False
        return True

    # --- familia / integrantes -------------------------------------------------
    def familia(self, id_familia: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM familias WHERE id_familia = ?", (id_familia,)
        ).fetchone()

    def integrantes(self, id_familia: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM integrantes WHERE id_familia = ?", (id_familia,)
        ).fetchall()

    def edad_anios(self, fecha_nac: str | None) -> int | None:
        if not fecha_nac:
            return None
        try:
            y, m, d = (int(x) for x in fecha_nac.split("-"))
            fn = dt.date(y, m, d)
            fy, fm, fd = (int(x) for x in self.fecha.split("-"))
            hoy = dt.date(fy, fm, fd)
        except (ValueError, AttributeError):
            return None
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

    def dias_desde_nacimiento(self, fecha_nac: str | None) -> int | None:
        if not fecha_nac:
            return None
        try:
            y, m, d = (int(x) for x in fecha_nac.split("-"))
            fn = dt.date(y, m, d)
            fy, fm, fd = (int(x) for x in self.fecha.split("-"))
            hoy = dt.date(fy, fm, fd)
        except (ValueError, AttributeError):
            return None
        return (hoy - fn).days

    # --- resolución EAV --------------------------------------------------------
    def _eav(self, tabla: str, id_col: str, id_val: str, tipo_col: str,
             tipo: str, subtipo: str, col_valor: str) -> Hecho | None:
        rows = self.conn.execute(
            f'SELECT * FROM "{tabla}" WHERE {id_col} = ? AND {tipo_col} = ? '
            f"AND (subtipo = ? OR ? IS NULL)",
            (id_val, tipo, subtipo, subtipo),
        ).fetchall()
        for r in rows:
            if not self._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                continue
            valor = r[col_valor]
            return Hecho(
                campo=f"{tipo}.{subtipo}",
                valor=_coerce(col_valor, valor),
                presente=valor is not None,
                acreditada=_as_bool(r["acreditada"]) if "acreditada" in r.keys() else True,
                estado_dato=r["estado_dato"] if "estado_dato" in r.keys() else "OBSERVADO",
                id_origen=_first_id(r),
            )
        return None


def umbral_regla(conn: sqlite3.Connection, fecha: str, campo_dato: str) -> int | float | None:
    """Valor del parámetro versionado que usa la regla de ``campo_dato`` a ``fecha``.

    Busca las reglas de ``campo_dato`` en las versiones de beneficio VIGENTES a
    ``fecha`` (semiabierta) y devuelve el ``valor_int``/``valor_decimal`` de su
    ``id_parametro_version`` como número (p. ej. ``semanas_gestacion`` ->
    ``R00301`` -> ``P006-02``). Falla cerrada (``None``) si no hay parámetro,
    hay más de un valor distinto o el valor no es numérico. Solo lectura.
    """
    filas = conn.execute(
        "SELECT p.valor_int, p.valor_decimal FROM reglas_elegibilidad r "
        "JOIN beneficios_versiones v ON v.id_version = r.id_version "
        "JOIN parametros_version p ON p.id_parametro = r.id_parametro_version "
        "WHERE r.campo_dato = ? AND (v.vigencia_desde IS NULL OR v.vigencia_desde <= ?) "
        "AND (v.vigencia_hasta IS NULL OR v.vigencia_hasta = '' OR ? < v.vigencia_hasta)",
        (campo_dato, fecha, fecha),
    ).fetchall()
    valores: set = set()
    for valor_int, valor_decimal in filas:
        crudo = valor_int if valor_int not in (None, "") else valor_decimal
        if crudo in (None, ""):
            return None
        try:
            s = str(crudo).strip()
            valores.add(int(s) if "." not in s else float(s))
        except (ValueError, TypeError):
            return None
    return valores.pop() if len(valores) == 1 else None


def _coerce(col_valor: str, valor):
    if valor is None:
        return None
    if col_valor == "valor_numero":
        try:
            return int(valor) if "." not in str(valor) else float(valor)
        except ValueError:
            return None
    if col_valor == "valor_booleano":
        return str(valor).strip().lower() == "true"
    return valor


def _as_bool(v):
    return str(v).strip().lower() == "true" if v is not None else False


def _first_id(row: sqlite3.Row):
    for k in row.keys():
        if k.startswith("id_"):
            return row[k]
    return None
