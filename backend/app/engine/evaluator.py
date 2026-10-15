"""Evaluador de elegibilidad por beneficio (M2).

Combina reglas (OR entre grupos, AND dentro), cuantificadores HOUSEHOLD/EXISTS/
COUNT, bindings por rol (misma entidad), lógica de 3 valores, nivel de confianza,
traza y monto estimado.
"""
from __future__ import annotations

import sqlite3

from . import operators as ops
from .facts import Repo
from .model import (Hecho, Nivel, ResultadoBeneficio, TrazaRegla, Tri,
                    MOTIVO_CRITERIO_NO_CUMPLE, MOTIVO_CRITERIOS_CUMPLEN,
                    MOTIVO_DATO_FALTANTE, MOTIVO_DATO_RSH_FALTANTE,
                    MOTIVO_EVIDENCIA_DECLARADA, MOTIVO_FUERA_DE_VIGENCIA)
from .resolver import FamiliaCtx, resolver_hogar, resolver_integrante


def _and_tri(valores: list[Tri]) -> Tri:
    """AND de 3 valores: algún NO -> NO; si no, algún IND -> IND; si no -> SI."""
    if any(v == Tri.NO for v in valores):
        return Tri.NO
    if any(v == Tri.INDETERMINADO for v in valores):
        return Tri.INDETERMINADO
    return Tri.SI


def _or_tri(valores: list[Tri]) -> Tri:
    """OR de 3 valores: algún SI -> SI; si no, algún IND -> IND; si no -> NO."""
    if any(v == Tri.SI for v in valores):
        return Tri.SI
    if any(v == Tri.INDETERMINADO for v in valores):
        return Tri.INDETERMINADO
    return Tri.NO


# Candidatos por rol (configurable). Devuelve integrantes elegibles como binding.
def _candidatos(rol: str, ctx: FamiliaCtx) -> list[sqlite3.Row]:
    ints = ctx.integrantes
    if rol in ("NINGUNO", "ACCESO"):
        return []
    if rol == "CAUSANTE":
        return [i for i in ints if _es_menor(ctx, i, 18) or _tiene_carga(ctx, i)]
    if rol == "ESTUDIANTE":
        return [i for i in ints if _tiene_condicion(ctx, i, "MATRICULA")]
    if rol == "GESTANTE":
        return [i for i in ints if _tiene_gestacion(ctx, i)]  # ninguno en el dataset
    if rol == "RECIEN_NACIDO":
        d = ctx.repo.dias_desde_nacimiento
        return [i for i in ints
                if (x := d(i["fecha_nacimiento_sintetica"])) is not None and x <= 90]
    if rol == "BENEFICIARIO":
        return [i for i in ints if i["parentesco"] in ("PERSONA_REFERENCIA", "PAREJA")]
    return list(ints)


def _es_menor(ctx, i, limite):
    e = ctx.repo.edad_anios(i["fecha_nacimiento_sintetica"])
    return e is not None and e < limite


def _tiene_carga(ctx, i):
    r = ctx.repo.conn.execute(
        "SELECT 1 FROM relaciones_integrantes WHERE id_integrante_origen = ? "
        "AND tipo_relacion = 'CARGA_DE' LIMIT 1", (i["id_integrante"],)
    ).fetchone()
    return r is not None


def _tiene_condicion(ctx, i, tipo):
    r = ctx.repo.conn.execute(
        "SELECT 1 FROM condiciones_integrante WHERE id_integrante = ? AND tipo_condicion = ? LIMIT 1",
        (i["id_integrante"], tipo)
    ).fetchone()
    return r is not None


def _tiene_gestacion(ctx, i):
    return False  # el dataset no trae datos de gestación


class Evaluator:
    def __init__(self, conn: sqlite3.Connection, fecha: str):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha
        self.repo = Repo(conn, fecha)

    def version_vigente(self, id_beneficio: str) -> sqlite3.Row | None:
        rows = self.conn.execute(
            "SELECT * FROM beneficios_versiones WHERE id_beneficio = ?", (id_beneficio,)
        ).fetchall()
        for r in rows:
            if Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                return r
        return None

    def _reglas(self, id_version: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM reglas_elegibilidad WHERE id_version = ? ORDER BY grupo_or, orden",
            (id_version,)
        ).fetchall()

    def _param(self, id_param: str | None) -> sqlite3.Row | None:
        if not id_param:
            return None
        return self.conn.execute(
            "SELECT * FROM parametros_version WHERE id_parametro = ?", (id_param,)
        ).fetchone()

    def _esperado(self, regla: sqlite3.Row):
        """Valor esperado: desde parámetro de versión o literal."""
        p = self._param(regla["id_parametro_version"])
        if p is not None:
            for col in ("valor_int", "valor_decimal", "valor_fecha", "valor_texto"):
                if p[col] not in (None, ""):
                    return p[col]
            return None
        return regla["valor_literal"]

    # --- evaluación de una regla atómica sobre una entidad --------------------
    def _eval_regla(self, regla, hecho: Hecho, cantidad_rel=None, pago_reciente=None,
                    ref_eq=None):
        op = regla["operador"]
        esperado = self._esperado(regla)
        obs = hecho.valor if hecho.presente else None

        if op == "EQ":
            return ops.op_eq(obs, esperado), esperado, None
        if op == "LT":
            return ops.op_lt(obs, esperado), esperado, None
        if op == "LTE":
            return ops.op_lte(obs, esperado), esperado, None
        if op == "GT":
            return ops.op_gt(obs, esperado), esperado, None
        if op == "GTE":
            return ops.op_gte(obs, esperado), esperado, None
        if op == "IN":
            return ops.op_in(obs, esperado), esperado, None
        if op == "BETWEEN":
            return ops.op_between(obs, esperado), esperado, None
        if op == "ACTIVE_ON_DATE":
            return ops.op_active_on_date(hecho), "activo", None
        if op == "RANGE_LOOKUP":
            tri, monto = ops.op_range_lookup(obs, esperado)
            return tri, esperado, monto
        if op == "COUNT_REL_GTE":
            return ops.op_count_rel_gte(cantidad_rel, esperado), esperado, None
        if op == "NOT_EXISTS_WITHIN":
            return ops.op_not_exists_within(pago_reciente), esperado, None
        if op == "REF_EQ":
            # REF_EQ se resuelve fuera (necesita la entidad ganadora del
            # binding_padre). El llamador pasa `ref_eq` ya evaluado como Tri.
            return (ref_eq if ref_eq is not None else Tri.INDETERMINADO), esperado, None
        return Tri.INDETERMINADO, esperado, None

    def _carga_acreditada_de(self, id_origen: str, id_destino: str | None) -> Tri:
        """REF_EQ `carga_acreditada_de`: ¿`origen` es carga acreditada y vigente
        de `destino` (el ganador del binding padre)?

        - Si aún no hay ganador del padre -> INDETERMINADO (no se puede resolver).
        - Si existe relación CARGA_DE acreditada y vigente origen->destino -> SI.
        - Si no -> NO.
        """
        if not id_destino:
            return Tri.INDETERMINADO
        rows = self.conn.execute(
            "SELECT acreditada, vigencia_desde, vigencia_hasta FROM relaciones_integrantes "
            "WHERE tipo_relacion = 'CARGA_DE' AND id_integrante_origen = ? "
            "AND id_integrante_destino = ?", (id_origen, id_destino)
        ).fetchall()
        for r in rows:
            if not Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                continue
            if str(r["acreditada"]).strip().lower() == "true":
                return Tri.SI
        return Tri.NO

    def evaluar(self, id_familia: str, id_beneficio: str,
                declarados: dict | None = None) -> ResultadoBeneficio:
        ctx = FamiliaCtx(self.repo, id_familia, declarados)
        version = self.version_vigente(id_beneficio)
        if version is None:
            return ResultadoBeneficio(
                id_familia=id_familia, id_beneficio=id_beneficio, id_version=None,
                fecha_evaluacion=self.fecha, resultado=Tri.NO,
                motivos=[MOTIVO_FUERA_DE_VIGENCIA])
        id_version = version["id_version"]
        reglas = self._reglas(id_version)

        # Agrupar por grupo_or
        grupos: dict[str, list] = {}
        for r in reglas:
            grupos.setdefault(r["grupo_or"], []).append(r)

        res = ResultadoBeneficio(
            id_familia=id_familia, id_beneficio=id_beneficio, id_version=id_version,
            fecha_evaluacion=self.fecha, resultado=Tri.NO)

        resultados_grupo: list[Tri] = []
        faltantes: set[str] = set()
        acreditacion_ok = True  # para nivel CONFIRMADO/PRELIMINAR

        for _, reglas_grupo in sorted(grupos.items()):
            tri_grupo, ganadores, trazas_g, falt_g, acred_g = self._eval_grupo(reglas_grupo, ctx)
            resultados_grupo.append(tri_grupo)
            res.traza.extend(trazas_g)
            if tri_grupo == Tri.SI:
                res.entidad_ganadora.update(ganadores)
                acreditacion_ok = acreditacion_ok and acred_g
            faltantes.update(falt_g)

        final = _or_tri(resultados_grupo)
        res.resultado = final
        if final == Tri.SI:
            res.nivel = Nivel.CONFIRMADO if acreditacion_ok else Nivel.PRELIMINAR
            res.motivos.append(MOTIVO_CRITERIOS_CUMPLEN)
            if any(t.nota == "declarado" and t.resultado == Tri.SI for t in res.traza):
                res.motivos.append(MOTIVO_EVIDENCIA_DECLARADA)
            res.monto_estimado = _num(version["monto_referencial_sintetico"])
        elif final == Tri.INDETERMINADO:
            res.datos_faltantes = sorted(faltantes)
            if "tramo_rsh" in faltantes:
                res.motivos.append(MOTIVO_DATO_RSH_FALTANTE)
            for f in sorted(faltantes):
                res.motivos.append(f"{MOTIVO_DATO_FALTANTE}:{f}")
        else:
            res.motivos.append(MOTIVO_CRITERIO_NO_CUMPLE)
        return res

    def _eval_grupo(self, reglas_grupo, ctx: FamiliaCtx):
        """Evalúa un grupo (AND dentro). Maneja HOUSEHOLD y EXISTS por binding."""
        # Separar reglas por binding
        por_binding: dict[str, list] = {}
        for r in reglas_grupo:
            por_binding.setdefault(r["binding_grupo"], []).append(r)

        tris: list[Tri] = []
        trazas: list[TrazaRegla] = []
        faltantes: set[str] = set()
        ganadores: dict[str, str] = {}
        acred_ok = True

        # Orden de evaluación: los bindings PADRE antes que sus hijos, para que
        # REF_EQ (p. ej. CAUSANTE_1 carga_de BENEFICIARIO_1) pueda resolverse
        # contra la entidad ya ganada del padre. HOGAR primero (no depende de
        # nadie); luego bindings sin binding_padre; luego los que lo tienen.
        def _orden(binding_reglas):
            binding, reglas_b = binding_reglas
            padre = reglas_b[0]["binding_padre"]
            if binding == "HOGAR":
                return 0
            return 1 if not padre else 2

        for binding, reglas_b in sorted(por_binding.items(), key=_orden):
            cuant = reglas_b[0]["cuantificador"]
            rol = reglas_b[0]["rol_causante"]

            if cuant == "HOUSEHOLD" or binding == "HOGAR":
                tri_b, trz, falt, acred = self._eval_binding_hogar(reglas_b, ctx)
                tris.append(tri_b)
                trazas.extend(trz)
                faltantes.update(falt)
                acred_ok = acred_ok and acred
            elif cuant in ("EXISTS", "COUNT"):
                tri_b, ganador, trz, falt, acred = self._eval_binding_exists(
                    reglas_b, ctx, rol, ganadores)
                tris.append(tri_b)
                trazas.extend(trz)
                faltantes.update(falt)
                if tri_b == Tri.SI and ganador:
                    ganadores[binding] = ganador
                    acred_ok = acred_ok and acred
            else:
                # ACCESO u otros: no soportado en M2 -> IND (se verá en M3).
                tris.append(Tri.INDETERMINADO)
                faltantes.add(reglas_b[0]["campo_dato"])

        return _and_tri(tris), ganadores, trazas, faltantes, acred_ok

    def _eval_binding_hogar(self, reglas_b, ctx: FamiliaCtx):
        tris, trazas, faltantes = [], [], set()
        acred_ok = True
        for r in reglas_b:
            campo = r["campo_dato"]
            hecho = resolver_hogar(campo, ctx)
            cantidad = pago = None
            tri, esperado, _monto = self._eval_regla(r, hecho, cantidad, pago)
            tris.append(tri)
            if tri == Tri.INDETERMINADO:
                faltantes.add(campo)
            if tri == Tri.SI and hecho.presente and not hecho.acreditada:
                acred_ok = False
            trazas.append(TrazaRegla(
                id_regla=r["id_regla"], campo=campo, operador=r["operador"],
                esperado=esperado, observado=(hecho.valor if hecho.presente else None),
                resultado=tri, binding_grupo=r["binding_grupo"], id_hecho=hecho.id_origen,
                nota=("declarado" if hecho.estado_dato == "DECLARADO" and hecho.presente else None)))
        return _and_tri(tris), trazas, faltantes, acred_ok

    def _eval_binding_exists(self, reglas_b, ctx: FamiliaCtx, rol: str,
                             ganadores_previos: dict[str, str] | None = None):
        """EXISTS: busca un integrante (misma persona) que cumpla todas las reglas.

        `ganadores_previos` trae las entidades ya ganadas de otros bindings del
        mismo grupo, para resolver REF_EQ contra el binding_padre.
        """
        ganadores_previos = ganadores_previos or {}
        candidatos = _candidatos(rol, ctx)
        if not candidatos:
            # Sin candidatos: si el motivo es falta de datos -> IND; si no -> NO.
            campos = {r["campo_dato"] for r in reglas_b}
            trazas = [TrazaRegla(
                id_regla=r["id_regla"], campo=r["campo_dato"], operador=r["operador"],
                esperado=self._esperado(r), observado=None, resultado=Tri.INDETERMINADO,
                binding_grupo=r["binding_grupo"], nota="sin candidatos") for r in reglas_b]
            return Tri.INDETERMINADO, None, trazas, campos, True

        mejor = (Tri.NO, None, [], set(), True)
        rank = {Tri.NO: 0, Tri.INDETERMINADO: 1, Tri.SI: 2}
        for cand in candidatos:
            tris, trazas, faltantes = [], [], set()
            acred_ok = True
            for r in reglas_b:
                campo = r["campo_dato"]
                hecho = resolver_integrante(campo, ctx, cand)
                cantidad = self._contar_hijos(ctx, cand) if r["operador"] == "COUNT_REL_GTE" else None
                # REF_EQ: resolver la relación carga_de contra el ganador del padre.
                ref_eq = None
                esperado_ref = None
                if r["operador"] == "REF_EQ":
                    padre = r["valor_binding_ref"] or r["binding_padre"]
                    id_destino = ganadores_previos.get(padre)
                    ref_eq = self._carga_acreditada_de(cand["id_integrante"], id_destino)
                    esperado_ref = f"carga_de:{padre}={id_destino or '?'}"
                tri, esperado, _ = self._eval_regla(r, hecho, cantidad, None, ref_eq)
                if esperado_ref is not None:
                    esperado = esperado_ref
                tris.append(tri)
                if tri == Tri.INDETERMINADO:
                    faltantes.add(campo)
                if tri == Tri.SI and hecho.presente and not hecho.acreditada:
                    acred_ok = False
                trazas.append(TrazaRegla(
                    id_regla=r["id_regla"], campo=campo, operador=r["operador"],
                    esperado=esperado, observado=(hecho.valor if hecho.presente else None),
                    resultado=tri, binding_grupo=r["binding_grupo"],
                    id_integrante_evaluado=cand["id_integrante"], id_hecho=hecho.id_origen,
                    nota=("declarado" if hecho.estado_dato == "DECLARADO" and hecho.presente else None)))
            tri_cand = _and_tri(tris)
            cur = (tri_cand, cand["id_integrante"], trazas, faltantes, acred_ok)
            if rank[tri_cand] > rank[mejor[0]]:
                mejor = cur
            if tri_cand == Tri.SI:
                break  # ganador encontrado
        return mejor

    def _contar_hijos(self, ctx, integrante):
        r = ctx.repo.conn.execute(
            "SELECT COUNT(*) FROM relaciones_integrantes WHERE id_integrante_origen = ? "
            "AND tipo_relacion = 'PROGENITOR_DE'", (integrante["id_integrante"],)
        ).fetchone()
        return r[0] if r else 0


def _num(v):
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None
