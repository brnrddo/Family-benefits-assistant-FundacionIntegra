"""Puente entre la pantalla "Agregar información" y el motor determinista (B2).

El endpoint ``POST /familias/{id}/antecedentes`` recibe los 18 campos de
``PreevaluationRequest`` más seis preguntas Sí/No (``CAMPOS_MOTOR``). Se
traducen al motor (ver ``PROPUESTA_ANTECEDENTES.md``):

- ``last_child_health_control_date`` -> ``dias_desde_control`` (R01203, V024) del
  niño o niña más joven.
- ``household_pregnancy`` -> hogar ``gestacion_declarada`` (habilita la candidata
  GESTANTE; ``False`` deja el beneficio de embarazo en NO).
- ``rsh_band`` -> hogar ``tramo_rsh``; ``has_incompatible_coverage`` -> hogar
  ``cobertura_incompatible`` (ambos solo como respaldo si la base no trae el dato).
- ``pregnancy_weeks_at_least_threshold`` -> ``semanas_gestacion`` de la gestante
  (Sí = N, No = N−1; N del parámetro de la regla vigente, nunca escrito aquí) y
  ``pregnancy_public_prenatal_control`` -> ``control_prenatal_red_publica``.
- ``pregnancy_public_network_delivery`` -> ``parto_red_publica`` y
  ``age_record_current`` -> ``antecedente_edad_vigente`` del niño o niña más joven.
- ``residence_requirement_met`` -> ``residencia_total_anios`` y
  ``residencia_ultimos20_anios`` de la persona de referencia (umbrales vigentes).

El resto (ingreso, Chile Crece Contigo, SSyO, discapacidad, terapia, vivienda,
empleo, agua, alimentación) no tiene ``campo_dato`` declarable en el motor.

Este módulo es puro (sin FastAPI): elige al integrante al que corresponde cada
dato y arma el dict ``declarados`` que consume ``engine.service.evaluar_familia``.
Un hecho declarado nunca viene acreditado -> el beneficio puede dar SI pero solo
como PRELIMINAR; nunca CONFIRMADO (lo garantiza el propio motor).
"""
from __future__ import annotations

import datetime as dt
import sqlite3

from app.engine.evaluator import gestante_declarada
from app.engine.facts import Repo, umbral_regla

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


def umbral_semanas_gestacion(conn: sqlite3.Connection, fecha_eval: str) -> int | None:
    """N de "¿Tiene N semanas o más?": parámetro de la regla vigente de
    ``semanas_gestacion`` (``R00301 -> P006-02``). ``None`` si no se puede leer."""
    n = umbral_regla(conn, fecha_eval, "semanas_gestacion")
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def _umbral_si_no(conn: sqlite3.Connection, fecha_eval: str, campo: str, cumple: bool):
    """Valor numérico que representa un Sí/No contra el umbral vigente de ``campo``.

    ``True`` -> el umbral (cumple ``GTE``); ``False`` -> umbral − 1 (no cumple).
    ``None`` si el umbral no se puede leer: el dato no se inyecta (sigue IND).
    """
    n = umbral_regla(conn, fecha_eval, campo)
    if n is None:
        return None
    return n if cumple else n - 1


def declarados_para_motor(
    conn: sqlite3.Connection,
    id_familia: str,
    campos: dict,
    fecha_eval: str,
) -> dict:
    """Dict ``declarados`` del motor a partir de los campos de la pantalla.

    ``campos`` es el cuerpo declarado (sin ``data_classification``) con valores
    conocidos ("No sé" ya omitido). Devuelve ``{"hogar": {...}, "integrante":
    {pid: {...}}}`` con claves solo si hay datos, o ``{}`` si no hay nada que el
    motor pueda usar.
    """
    hogar: dict = {}
    integrante: dict[str, dict] = {}

    def poner(pid: str | None, campo: str, valor) -> None:
        if pid is not None and valor is not None:
            integrante.setdefault(pid, {})[campo] = valor

    # Fecha del último control de salud -> días, del niño o niña más joven.
    fecha_control = campos.get(CAMPO_FECHA_CONTROL)
    if fecha_control:
        dias = dias_desde_fecha(str(fecha_control), fecha_eval)
        if dias is not None:
            poner(nino_mas_joven(conn, id_familia, fecha_eval), CAMPO_MOTOR_CONTROL, dias)

    # Hogar.
    if isinstance(campos.get("household_pregnancy"), bool):
        hogar["gestacion_declarada"] = campos["household_pregnancy"]
    if campos.get("rsh_band") is not None:
        hogar["tramo_rsh"] = campos["rsh_band"]
    if isinstance(campos.get("has_incompatible_coverage"), bool):
        hogar["cobertura_incompatible"] = campos["has_incompatible_coverage"]

    # Gestante: misma persona que elige el motor para el candidato GESTANTE.
    semanas = campos.get("pregnancy_weeks_at_least_threshold")
    prenatal = campos.get("pregnancy_public_prenatal_control")
    if isinstance(semanas, bool) or isinstance(prenatal, bool):
        gestante = gestante_declarada(Repo(conn, fecha_eval).integrantes(id_familia))
        pid_g = gestante["id_integrante"] if gestante is not None else None
        if isinstance(semanas, bool):
            poner(pid_g, "semanas_gestacion",
                  _umbral_si_no(conn, fecha_eval, "semanas_gestacion", semanas))
        if isinstance(prenatal, bool):
            poner(pid_g, "control_prenatal_red_publica", prenatal)

    # Niño o niña más joven.
    parto = campos.get("pregnancy_public_network_delivery")
    edad_vigente = campos.get("age_record_current")
    if isinstance(parto, bool) or isinstance(edad_vigente, bool):
        pid_n = nino_mas_joven(conn, id_familia, fecha_eval)
        if isinstance(parto, bool):
            poner(pid_n, "parto_red_publica", parto)
        if isinstance(edad_vigente, bool):
            poner(pid_n, "antecedente_edad_vigente", edad_vigente)

    # Residencia: persona de referencia, ambos umbrales vigentes.
    residencia = campos.get("residence_requirement_met")
    if isinstance(residencia, bool):
        ref = next((i for i in Repo(conn, fecha_eval).integrantes(id_familia)
                    if i["parentesco"] == "PERSONA_REFERENCIA"), None)
        pid_r = ref["id_integrante"] if ref is not None else None
        for campo in ("residencia_total_anios", "residencia_ultimos20_anios"):
            poner(pid_r, campo, _umbral_si_no(conn, fecha_eval, campo, residencia))

    declarados: dict = {}
    if hogar:
        declarados["hogar"] = hogar
    if integrante:
        declarados["integrante"] = integrante
    return declarados
