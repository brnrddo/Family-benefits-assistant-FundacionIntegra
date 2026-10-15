"""Operadores atómicos del motor (M2).

Cada operador compara un valor observado contra un esperado y devuelve Tri
(SI / NO / INDETERMINADO). Si el valor observado no está presente -> INDETERMINADO.

Operadores presentes en reglas_elegibilidad.csv (verificado):
  ACTIVE_ON_DATE, LTE, EQ, IN, GTE, LT, RANGE_LOOKUP, REF_EQ, BETWEEN,
  COUNT_REL_GTE, NOT_EXISTS_WITHIN.
"""
from __future__ import annotations

import json
import re

from .model import Hecho, Tri


def _num(x):
    """Convierte a número (int/float) o None si no se puede."""
    if x is None:
        return None
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x
    s = str(x).strip()
    if s == "":
        return None
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def _parse_lista(literal) -> list | None:
    """Parsea un literal que puede ser lista JSON (ENUM_LIST) o escalar."""
    if literal is None:
        return None
    if isinstance(literal, (list, tuple)):
        return list(literal)
    s = str(literal).strip()
    if s.startswith("["):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None
    return [s]


# --- comparadores escalares ---------------------------------------------------

def op_eq(observado, esperado) -> Tri:
    if observado is None:
        return Tri.INDETERMINADO
    # Normaliza booleanos expresados como texto.
    def norm(v):
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("true", "false"):
            return s == "true"
        return str(v).strip()
    return Tri.SI if norm(observado) == norm(esperado) else Tri.NO


def _cmp(observado, esperado, fn) -> Tri:
    o, e = _num(observado), _num(esperado)
    if o is None or e is None:
        return Tri.INDETERMINADO
    return Tri.SI if fn(o, e) else Tri.NO


def op_lt(o, e):  return _cmp(o, e, lambda a, b: a < b)
def op_lte(o, e): return _cmp(o, e, lambda a, b: a <= b)
def op_gt(o, e):  return _cmp(o, e, lambda a, b: a > b)
def op_gte(o, e): return _cmp(o, e, lambda a, b: a >= b)


def op_in(observado, esperado_lista) -> Tri:
    if observado is None:
        return Tri.INDETERMINADO
    lista = _parse_lista(esperado_lista)
    if not lista:
        return Tri.INDETERMINADO
    return Tri.SI if str(observado).strip() in [str(x) for x in lista] else Tri.NO


def op_between(observado, rango) -> Tri:
    """BETWEEN sobre un RANGE_LIST tipo ``[4,19)`` (respeta abiertos/cerrados)."""
    o = _num(observado)
    if o is None:
        return Tri.INDETERMINADO
    rng = _parse_rango(rango)
    if rng is None:
        return Tri.INDETERMINADO
    (lo, lo_incl), (hi, hi_incl) = rng
    ok_lo = (o >= lo) if lo_incl else (o > lo)
    ok_hi = (o <= hi) if hi_incl else (o < hi)
    return Tri.SI if (ok_lo and ok_hi) else Tri.NO


def _parse_rango(texto):
    """Parsea ``[4,19)`` -> ((4, True), (19, False)). None si no matchea."""
    if texto is None:
        return None
    m = re.match(r"\s*([\[\(])\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*([\]\)])\s*",
                 str(texto))
    if not m:
        return None
    lb, lo, hi, rb = m.groups()
    return ((_num(lo), lb == "["), (_num(hi), rb == "]"))


def op_range_lookup(observado, range_list) -> tuple[Tri, int | None]:
    """RANGE_LOOKUP sobre ``(0,300000]:22000;(300000,450000]:14000;...``.

    Devuelve (Tri, monto_del_tramo). Cumple si el valor cae en algún tramo.
    """
    o = _num(observado)
    if o is None:
        return Tri.INDETERMINADO, None
    if range_list is None:
        return Tri.INDETERMINADO, None
    for parte in str(range_list).split(";"):
        parte = parte.strip()
        if not parte or ":" not in parte:
            continue
        rango_txt, monto_txt = parte.rsplit(":", 1)
        rng = _parse_rango(rango_txt)
        if rng is None:
            continue
        (lo, lo_incl), (hi, hi_incl) = rng
        ok_lo = (o >= lo) if lo_incl else (o > lo)
        ok_hi = (o <= hi) if hi_incl else (o < hi)
        if ok_lo and ok_hi:
            return Tri.SI, _num(monto_txt)
    return Tri.NO, None


def op_active_on_date(hecho: Hecho) -> Tri:
    """ACTIVE_ON_DATE: el hecho existe y está en estado activo a la fecha.

    La vigencia ya se filtró al resolver el hecho (solo se resuelven hechos
    vigentes a la fecha de evaluación). Aquí basta con que el hecho exista y,
    si tiene un valor de estado, que éste indique actividad.
    """
    if not hecho.presente:
        return Tri.INDETERMINADO
    v = hecho.valor
    if isinstance(v, bool):
        return Tri.SI if v else Tri.NO
    s = str(v).strip().upper() if v is not None else ""
    if s in ("TRUE",):
        return Tri.SI
    if s in ("FALSE",):
        return Tri.NO
    estados_activos = {"ACTIVA", "EN_CURSO", "VIGENTE", "APROBADA"}
    if s in estados_activos:
        return Tri.SI
    estados_inactivos = {"INACTIVA", "FINALIZADA", "TERMINADA", "RECHAZADA",
                         "SUSPENDIDA", "ANULADA", "VENCIDA"}
    if s in estados_inactivos:
        return Tri.NO
    # Algunos campos de "vigencia" apuntan a una columna que NO guarda un estado
    # sino una categoría cuya mera presencia vigente certifica actividad (p. ej.
    # ``discapacidad_vigencia`` resuelve sobre DISCAPACIDAD.SEVERIDAD, cuyo valor
    # es LEVE/MODERADA/SEVERA). Para esos valores conocidos, existir vigente =
    # activo -> SI.
    severidades_vigentes = {"LEVE", "MODERADA", "SEVERA"}
    if s in severidades_vigentes:
        return Tri.SI
    # Presente pero con un valor NO reconocido: no se infiere actividad. Antes
    # se asumía SI ("activo por existir vigente"), lo que inventaba un SI ante un
    # dato ambiguo; ahora se devuelve INDETERMINADO para no afirmar lo que no se
    # sabe (coherente con el principio del motor: sin dato claro -> IND).
    return Tri.INDETERMINADO


def op_count_rel_gte(cantidad: int | None, minimo) -> Tri:
    if cantidad is None:
        return Tri.INDETERMINADO
    e = _num(minimo)
    if e is None:
        return Tri.INDETERMINADO
    return Tri.SI if cantidad >= e else Tri.NO


def op_not_exists_within(existe_pago_reciente: bool | None) -> Tri:
    """NOT_EXISTS_WITHIN: cumple si NO hay pago en la ventana. None -> IND."""
    if existe_pago_reciente is None:
        return Tri.INDETERMINADO
    return Tri.NO if existe_pago_reciente else Tri.SI
