"""Puente entre la pantalla "Agregar información" y el motor determinista (B2).

El endpoint ``POST /familias/{id}/antecedentes`` recibe hasta 18 campos
declarados por la familia (``models_antecedentes.CAMPO_A_MISSING_CODE``). De
esos, el ÚNICO que el motor de reglas puede convertir en elegibilidad hoy es la
fecha del último control de salud del niño o niña: la regla ``R01203`` del
subsistema SSyO (versión vigente ``V024``) compara ``dias_desde_control`` con
un umbral (``LTE``). El resto de los campos no tiene un ``campo_dato`` del motor
al que mapear (ver ``PROPUESTA_ANTECEDENTES.md``):

- ``household_pregnancy`` llega como booleano; el motor pide ``semanas_gestacion``
  (número). De un sí/no no se puede derivar un número de semanas sin inventar,
  así que NO se mapea (seguiría solo resolviendo su ``missing_code``).
- RSH, ingreso, Chile Crece Contigo y SSyO vienen de registros oficiales: no son
  declarables por diseño.
- Discapacidad, terapia, vivienda, empleo, agua y alimentación no existen como
  ``campo_dato`` del motor.

Este módulo es puro (sin FastAPI): convierte la fecha a días, elige al
integrante al que corresponde el dato (el niño o niña MÁS JOVEN de la familia)
y arma el dict ``declarados`` que consume ``engine.service.evaluar_familia``.
Un hecho declarado nunca viene acreditado -> el beneficio puede dar SI pero solo
como PRELIMINAR; nunca CONFIRMADO (lo garantiza el propio motor).
"""
from __future__ import annotations

import datetime as dt
import sqlite3

# Campo de la pantalla cuya fecha se convierte a ``dias_desde_control`` del motor.
CAMPO_FECHA_CONTROL = "last_child_health_control_date"
# ``campo_dato`` del motor (integrante) que alimenta la regla R01203 (V024).
CAMPO_MOTOR_CONTROL = "dias_desde_control"
_MAYORIA_EDAD = 18


def dias_desde_fecha(fecha_control: str, fecha_eval: str) -> int | None:
    """Días transcurridos entre ``fecha_control`` y la fecha de evaluación.

    Ambas en ``YYYY-MM-DD``. Devuelve un entero >= 0 (una fecha de control en el
    futuro respecto de la evaluación se trata como 0 días, no negativa) o
    ``None`` si alguna fecha es ilegible. No inventa valores: ante la duda, el
    campo sigue INDETERMINADO en el motor.
    """
    try:
        control = dt.date.fromisoformat(fecha_control)
        evaluacion = dt.date.fromisoformat(fecha_eval)
    except (ValueError, TypeError):
        return None
    dias = (evaluacion - control).days
    return dias if dias > 0 else 0


def nino_mas_joven(conn: sqlite3.Connection, id_familia: str, fecha_eval: str) -> str | None:
    """``id_integrante`` del menor de 18 con la fecha de nacimiento más reciente.

    El control de salud infantil es de un niño o niña concreto; la pantalla no
    identifica al integrante, así que se resuelve aquí contra la base: entre los
    menores de 18 de la familia se elige al MÁS JOVEN (fecha de nacimiento más
    reciente). ``None`` si la familia no tiene menores: en ese caso el dato no
    se inyecta y la elegibilidad no cambia por esta vía.
    """
    conn.row_factory = sqlite3.Row
    try:
        corte = dt.date.fromisoformat(fecha_eval)
    except (ValueError, TypeError):
        return None
    filas = conn.execute(
        "SELECT id_integrante, fecha_nacimiento_sintetica FROM integrantes "
        "WHERE id_familia = ?",
        (id_familia,),
    ).fetchall()

    mejor_id: str | None = None
    mejor_nac: dt.date | None = None
    for fila in filas:
        nac_raw = fila["fecha_nacimiento_sintetica"]
        try:
            nac = dt.date.fromisoformat(str(nac_raw))
        except (ValueError, TypeError):
            continue
        edad = corte.year - nac.year - ((corte.month, corte.day) < (nac.month, nac.day))
        if edad < 0 or edad >= _MAYORIA_EDAD:
            continue
        # Fecha de nacimiento más reciente = más joven. Empate: id menor (estable).
        if mejor_nac is None or nac > mejor_nac or (nac == mejor_nac and fila["id_integrante"] < mejor_id):
            mejor_id = fila["id_integrante"]
            mejor_nac = nac
    return mejor_id


def declarados_para_motor(
    conn: sqlite3.Connection,
    id_familia: str,
    campos: dict,
    fecha_eval: str,
) -> dict:
    """Dict ``declarados`` del motor a partir de los campos de la pantalla.

    ``campos`` es el cuerpo declarado (sin ``data_classification``). Hoy solo se
    traduce ``last_child_health_control_date`` -> ``dias_desde_control`` del niño
    más joven. Devuelve ``{}`` si no hay nada que el motor pueda usar (p. ej. no
    se declaró la fecha, es ilegible, o la familia no tiene menores): en ese caso
    el llamador no debe reevaluar con el motor.
    """
    fecha_control = campos.get(CAMPO_FECHA_CONTROL)
    if not fecha_control:
        return {}
    dias = dias_desde_fecha(str(fecha_control), fecha_eval)
    if dias is None:
        return {}
    pid = nino_mas_joven(conn, id_familia, fecha_eval)
    if pid is None:
        return {}
    return {"integrante": {pid: {CAMPO_MOTOR_CONTROL: dias}}}
