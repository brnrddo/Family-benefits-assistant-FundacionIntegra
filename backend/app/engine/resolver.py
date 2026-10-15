"""Resuelve un ``campo_dato`` a un Hecho, para hogar o integrante (M2).

Centraliza el mapa campo->origen (directo / EAV / derivado / faltante). El
evaluador llama a ``resolver(campo, ctx, entidad)`` y recibe un Hecho.
"""
from __future__ import annotations

import sqlite3

from ..config import SUPONER_ANTECEDENTE_EDAD, SUPONER_CONTROL_VIGENTE
from .facts import (CAMPOS_FALTANTES, EAV_HOGAR, EAV_INTEGRANTE, Repo)
from .model import Hecho


class FamiliaCtx:
    """Contexto resuelto de una familia para evaluar beneficios."""

    def __init__(self, repo: Repo, id_familia: str):
        self.repo = repo
        self.id_familia = id_familia
        self.familia = repo.familia(id_familia)
        self.integrantes = repo.integrantes(id_familia)

    def existe(self) -> bool:
        return self.familia is not None


def _hogar_directo(campo: str, ctx: FamiliaCtx) -> Hecho | None:
    f = ctx.familia
    if f is None:
        return None
    if campo == "tramo_rsh":
        v = f["tramo_rsh_corte"]
        return Hecho(campo=campo, valor=_num_or_none(v), presente=v not in (None, ""),
                     id_origen=f["id_familia"])
    return None


def _hogar_derivado(campo: str, ctx: FamiliaCtx) -> Hecho | None:
    if campo == "ingreso_per_capita":
        ingreso = _eav_hogar_valor(ctx, "INGRESO_HOGAR", "MONTO")
        n = _num_or_none(ctx.familia["numero_integrantes_corte"]) if ctx.familia else None
        if ingreso is None or not n:
            return Hecho(campo=campo, presente=False)
        return Hecho(campo=campo, valor=int(ingreso / n), presente=True)
    if campo == "gasto_agua_pct_ingreso":
        agua = _eav_hogar_valor(ctx, "BOLETA_AGUA", "MONTO")
        ingreso = _eav_hogar_valor(ctx, "INGRESO_HOGAR", "MONTO")
        if agua is None or not ingreso:
            return Hecho(campo=campo, presente=False)
        return Hecho(campo=campo, valor=round(agua / ingreso * 100, 4), presente=True)
    if campo == "mora_dias":
        v = _eav_hogar_valor(ctx, "BOLETA_AGUA", "MORA_DIAS")
        return Hecho(campo=campo, valor=v, presente=v is not None)
    if campo == "comuna_cuenta_coincide_residencia":
        cuenta = _eav_hogar_valor(ctx, "BOLETA_AGUA", "COMUNA_CUENTA")
        resid = _eav_hogar_valor(ctx, "RESIDENCIA", "COMUNA")
        if cuenta is None or resid is None:
            return Hecho(campo=campo, presente=False)
        return Hecho(campo=campo, valor=(str(cuenta) == str(resid)), presente=True)
    return None


def _eav_hogar_valor(ctx: FamiliaCtx, tipo: str, subtipo: str):
    """Devuelve el valor crudo (numérico/texto) de un antecedente del hogar vigente."""
    rows = ctx.repo.conn.execute(
        "SELECT * FROM antecedentes_familia WHERE id_familia = ? AND tipo_antecedente = ? "
        "AND subtipo = ?",
        (ctx.id_familia, tipo, subtipo),
    ).fetchall()
    for r in rows:
        if not Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], ctx.repo.fecha):
            continue
        for col in ("valor_numero", "valor_texto", "valor_booleano", "valor_fecha"):
            if r[col] not in (None, ""):
                v = r[col]
                if col == "valor_numero":
                    return _num_or_none(v)
                if col == "valor_booleano":
                    return str(v).strip().lower() == "true"
                return v
    return None


def resolver_hogar(campo: str, ctx: FamiliaCtx) -> Hecho:
    if campo in CAMPOS_FALTANTES:
        return Hecho(campo=campo, presente=False)
    h = _hogar_directo(campo, ctx)
    if h is not None:
        return h
    h = _hogar_derivado(campo, ctx)
    if h is not None:
        return h
    if campo in EAV_HOGAR:
        tipo, subtipo, col = EAV_HOGAR[campo]
        hecho = ctx.repo._eav("antecedentes_familia", "id_familia", ctx.id_familia,
                              "tipo_antecedente", tipo, subtipo, col)
        return hecho or Hecho(campo=campo, presente=False)
    # subtramo del hogar (rsh_historial)
    if campo == "subtramo_sintetico":
        r = ctx.repo.conn.execute(
            "SELECT subtramo_sintetico, vigencia_desde, vigencia_hasta FROM rsh_historial "
            "WHERE id_familia = ?", (ctx.id_familia,)
        ).fetchall()
        for row in r:
            if Repo._vig(row["vigencia_desde"], row["vigencia_hasta"], ctx.repo.fecha):
                v = row["subtramo_sintetico"]
                return Hecho(campo=campo, valor=_num_or_none(v), presente=v not in (None, ""))
    return Hecho(campo=campo, presente=False)


def resolver_integrante(campo: str, ctx: FamiliaCtx, integrante: sqlite3.Row) -> Hecho:
    pid = integrante["id_integrante"]

    # --- Supuestos configurables sobre campos ausentes (opción b) ------------
    if campo == "antecedente_edad_vigente" and SUPONER_ANTECEDENTE_EDAD:
        # Evidencia indirecta: ser menor de 18 es lo que certifica el antecedente.
        edad = ctx.repo.edad_anios(integrante["fecha_nacimiento_sintetica"])
        if edad is not None and edad < 18:
            return Hecho(campo=campo, valor=True, presente=True,
                         acreditada=False, estado_dato="DECLARADO", id_origen=pid)
        return Hecho(campo=campo, presente=False, id_origen=pid)

    if campo == "dias_desde_control" and SUPONER_CONTROL_VIGENTE:
        # Evidencia indirecta: existe un control de salud infantil vigente.
        tipo, subtipo, col = EAV_INTEGRANTE.get(
            "control_infantil_red_publica", ("CONTROL_SALUD", "INFANTIL_RED_PUBLICA", "valor_booleano"))
        hecho_control = ctx.repo._eav("condiciones_integrante", "id_integrante", pid,
                                      "tipo_condicion", tipo, subtipo, col)
        if hecho_control and hecho_control.presente and hecho_control.valor:
            # Se asume dentro de ventana (valor 0 días desde el control).
            return Hecho(campo=campo, valor=0, presente=True,
                         acreditada=False, estado_dato="DECLARADO", id_origen=pid)
        return Hecho(campo=campo, presente=False, id_origen=pid)

    if campo in CAMPOS_FALTANTES:
        return Hecho(campo=campo, presente=False, id_origen=pid)
    if campo == "edad":
        v = ctx.repo.edad_anios(integrante["fecha_nacimiento_sintetica"])
        return Hecho(campo=campo, valor=v, presente=v is not None, id_origen=pid)
    if campo == "edad_meses":
        d = ctx.repo.dias_desde_nacimiento(integrante["fecha_nacimiento_sintetica"])
        return Hecho(campo=campo, valor=(d // 30 if d is not None else None),
                     presente=d is not None, id_origen=pid)
    if campo == "dias_desde_nacimiento":
        v = ctx.repo.dias_desde_nacimiento(integrante["fecha_nacimiento_sintetica"])
        return Hecho(campo=campo, valor=v, presente=v is not None, id_origen=pid)
    if campo == "sexo_registral":
        v = integrante["sexo_registral_sintetico"]
        return Hecho(campo=campo, valor=v, presente=v not in (None, ""), id_origen=pid)
    if campo in EAV_INTEGRANTE:
        tipo, subtipo, col = EAV_INTEGRANTE[campo]
        hecho = ctx.repo._eav("condiciones_integrante", "id_integrante", pid,
                              "tipo_condicion", tipo, subtipo, col)
        return hecho or Hecho(campo=campo, presente=False, id_origen=pid)
    return Hecho(campo=campo, presente=False, id_origen=pid)


def _num_or_none(v):
    if v in (None, ""):
        return None
    try:
        return int(v) if "." not in str(v) else float(v)
    except ValueError:
        return None
