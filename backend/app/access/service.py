"""Servicio de estado de acceso + checklist (M3)."""
from __future__ import annotations

import sqlite3

from ..config import DB_PATH, FECHA_EVALUACION
from ..engine.evaluator import Evaluator
from ..engine.facts import DOCUMENTO_POR_CAMPO
from ..engine.model import Nivel, Tri
from .model import (Checklist, EstadoAcceso, RequisitoDoc, ResultadoAcceso,
                    SEMAFORO)

# Estados de una postulación considerados "en curso".
EN_CURSO = {"POSTULADA", "EN_REVISION", "DERIVADA", "APROBADA"}

# Beneficio con cupo contingente (Canasta Familiar, privado sintético).
# El cupo real se lee de la versión vigente (cupo_contingente); este es el
# fallback si la versión no lo trae.
BEN_CUPO = "BEN-018"
CUPO_BEN018_DEFAULT = 75


def _conn(db_path=None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or DB_PATH))
    c.row_factory = sqlite3.Row
    return c


class AccesoService:
    def __init__(self, conn: sqlite3.Connection, fecha: str = FECHA_EVALUACION):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha
        self.ev = Evaluator(conn, fecha)
        # Cache del cupo de BEN-018: {id_familia dentro del cupo}. Se calcula una
        # sola vez por servicio (cálculo colectivo, no por familia).
        self._dentro_cupo: set[str] | None = None

    # --- gestiones -----------------------------------------------------------
    def _ultima_postulacion(self, id_familia: str, id_beneficio: str):
        """Postulación más reciente de la familia para el beneficio."""
        rows = self.conn.execute(
            "SELECT * FROM postulaciones WHERE id_familia = ? AND id_beneficio = ? "
            "ORDER BY fecha_hora_inicio DESC", (id_familia, id_beneficio)
        ).fetchall()
        return rows[0] if rows else None

    def _ultimo_estado(self, id_postulacion: str) -> str | None:
        row = self.conn.execute(
            "SELECT estado FROM postulaciones_estados WHERE id_postulacion = ? "
            "ORDER BY CAST(secuencia AS INTEGER) DESC LIMIT 1", (id_postulacion,)
        ).fetchone()
        return row[0] if row else None

    # --- checklist -----------------------------------------------------------
    def _fuente_url(self, id_beneficio: str) -> str | None:
        row = self.conn.execute(
            """SELECT f.url FROM beneficios_fuentes bf
               JOIN fuentes f ON f.id_fuente = bf.id_fuente
               WHERE bf.id_beneficio = ? AND f.url IS NOT NULL AND f.url != ''
               LIMIT 1""", (id_beneficio,)
        ).fetchone()
        return row[0] if row else None

    def _construir_checklist(self, id_beneficio: str, version, elegibilidad) -> Checklist:
        ben = self.conn.execute(
            "SELECT plataforma_canal_principal FROM beneficios WHERE id_beneficio = ?",
            (id_beneficio,)
        ).fetchone()
        canal = ben["plataforma_canal_principal"] if ben else None

        requiere = str(version["requiere_accion_familia"]).strip().lower() == "true" \
            if version else False

        # Documentos: derivados de los campo_dato de la traza de elegibilidad.
        docs: list[RequisitoDoc] = []
        vistos = set()
        for t in elegibilidad.get("traza", []):
            campo = t["campo"]
            if campo in vistos:
                continue
            doc = DOCUMENTO_POR_CAMPO.get(campo)
            if not doc:
                continue
            vistos.add(campo)
            res = t["resultado"]
            docs.append(RequisitoDoc(
                campo=campo, documento=doc,
                cumplido=(res == "SI"),
                faltante=(res == "INDETERMINADO"),
            ))

        return Checklist(
            modalidad_acceso=version["modalidad_acceso"] if version else None,
            requiere_accion_familia=requiere,
            canal=canal,
            ventana_desde=version["ventana_acceso_desde"] if version else None,
            ventana_hasta=version["ventana_acceso_hasta"] if version else None,
            fuente_url=self._fuente_url(id_beneficio),
            documentos=docs,
        )

    # --- cupo BEN-018 (Canasta Familiar) -------------------------------------
    def _cupo_ben018(self) -> int:
        """Cupo de la versión vigente de BEN-018 (fallback a 75)."""
        version = self.ev.version_vigente(BEN_CUPO)
        if version is not None:
            raw = version["cupo_contingente"]
            try:
                if raw not in (None, ""):
                    return int(raw)
            except (ValueError, TypeError):
                pass
        return CUPO_BEN018_DEFAULT

    def _eav_hogar_num(self, id_familia: str, tipo: str, subtipo: str):
        """Valor numérico de un antecedente del hogar vigente (o None)."""
        rows = self.conn.execute(
            "SELECT valor_numero, vigencia_desde, vigencia_hasta FROM antecedentes_familia "
            "WHERE id_familia = ? AND tipo_antecedente = ? AND subtipo = ?",
            (id_familia, tipo, subtipo),
        ).fetchall()
        from ..engine.facts import Repo
        for r in rows:
            if not Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                continue
            v = r["valor_numero"]
            if v in (None, ""):
                continue
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None

    def _familias_dentro_cupo(self) -> set[str]:
        """Set de familias de BEN-018 que caen DENTRO del cupo.

        Spec §7: ordenar elegibles (resultado SI) por índice de inseguridad
        descendente, luego ingreso per cápita ascendente, luego id; las primeras
        ``cupo`` entran, el resto queda SIN_CUPO.
        """
        if self._dentro_cupo is not None:
            return self._dentro_cupo

        cupo = self._cupo_ben018()
        elegibles: list[tuple] = []
        familias = [r[0] for r in self.conn.execute(
            "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
        for fam in familias:
            elig = self.ev.evaluar(fam, BEN_CUPO)
            if elig.resultado != Tri.SI:
                continue
            inseguridad = self._eav_hogar_num(fam, "INSEGURIDAD_ALIMENTARIA", "INDICE") or 0.0
            ingreso = self._eav_hogar_num(fam, "INGRESO_HOGAR", "MONTO")
            n = self.conn.execute(
                "SELECT numero_integrantes_corte FROM familias WHERE id_familia = ?",
                (fam,)).fetchone()[0]
            try:
                pc = (ingreso / float(n)) if (ingreso is not None and n) else float("inf")
            except (ValueError, TypeError, ZeroDivisionError):
                pc = float("inf")
            # Orden: inseguridad DESC, ingreso_pc ASC, id ASC.
            elegibles.append((-inseguridad, pc, fam))

        elegibles.sort()
        self._dentro_cupo = {fam for _, _, fam in elegibles[:cupo]}
        return self._dentro_cupo

    # --- estado de acceso ----------------------------------------------------
    def evaluar(self, id_familia: str, id_beneficio: str) -> ResultadoAcceso:
        elig = self.ev.evaluar(id_familia, id_beneficio)
        elig_dict = elig.to_dict()
        preliminar = elig.nivel == Nivel.PRELIMINAR

        post = self._ultima_postulacion(id_familia, id_beneficio)
        id_post = post["id_postulacion"] if post else None
        ultimo = self._ultimo_estado(id_post) if id_post else None
        tiene_gestion = post is not None

        version = self.ev.version_vigente(id_beneficio)

        estado = self._derivar_estado(id_familia, elig.resultado, preliminar, tiene_gestion,
                                      ultimo, id_beneficio)

        # Checklist solo tiene sentido cuando puede calificar (SI o IND con criterios).
        checklist = None
        if elig.resultado in (Tri.SI, Tri.INDETERMINADO) and version is not None:
            checklist = self._construir_checklist(id_beneficio, version, elig_dict)

        return ResultadoAcceso(
            id_familia=id_familia, id_beneficio=id_beneficio,
            estado=estado, semaforo=SEMAFORO[estado], preliminar=preliminar,
            tiene_gestion=tiene_gestion, ultimo_estado_gestion=ultimo,
            id_postulacion=id_post, checklist=checklist, elegibilidad=elig_dict,
        )

    def _derivar_estado(self, id_familia: str, resultado: Tri, preliminar: bool,
                        tiene_gestion: bool, ultimo: str | None,
                        id_beneficio: str) -> EstadoAcceso:
        if resultado == Tri.NO:
            return EstadoAcceso.NO_APLICA
        if resultado == Tri.INDETERMINADO:
            return EstadoAcceso.INDETERMINADO

        # resultado == SI
        if tiene_gestion:
            if ultimo == "VIGENTE":
                return EstadoAcceso.ASIGNADO
            if ultimo == "RECHAZADA":
                return EstadoAcceso.GESTION_RECHAZADA
            if ultimo in EN_CURSO:
                return EstadoAcceso.GESTION_EN_CURSO
            # estado desconocido con gestión: tratarlo como en curso
            return EstadoAcceso.GESTION_EN_CURSO

        # SI sin gestión:
        # BEN-018 tiene cupo contingente: si la familia es elegible pero queda
        # sobre el cupo (posición > cupo), es SIN_CUPO (spec §7).
        if id_beneficio == BEN_CUPO and id_familia not in self._familias_dentro_cupo():
            return EstadoAcceso.SIN_CUPO

        # decisión [3] del usuario: preliminar prima -> PENDIENTE_ANTECEDENTES
        if preliminar:
            return EstadoAcceso.PENDIENTE_ANTECEDENTES
        return EstadoAcceso.ELEGIBLE_SIN_ASIGNACION  # LA BRECHA

    def estado_reevaluado(self, id_familia: str, res) -> tuple[EstadoAcceso, bool]:
        """Acceso de un resultado REEVALUADO en memoria con datos declarados.

        DEC-082 (desviación consciente de la decisión [3], solo en esta vía): lo
        que la familia respondió pasa a "aplica", así que un SI sin gestión queda
        ``ELEGIBLE_SIN_ASIGNACION`` aunque sea PRELIMINAR (el nivel lo sigue
        dando el motor). Con gestión -> ASIGNADO/GESTION_*; BEN-018 respeta cupo;
        IND -> INDETERMINADO; NO -> NO_APLICA. ``evaluar()`` no cambia.
        Devuelve ``(estado, requiere_accion_familia)``.
        """
        post = self._ultima_postulacion(id_familia, res.id_beneficio)
        ultimo = self._ultimo_estado(post["id_postulacion"]) if post else None
        estado = self._derivar_estado(id_familia, res.resultado, False, post is not None,
                                      ultimo, res.id_beneficio)
        version = self.ev.version_vigente(res.id_beneficio)
        requiere = (str(version["requiere_accion_familia"]).strip().lower() == "true"
                    if version is not None else False)
        return estado, requiere

    def evaluar_familia(self, id_familia: str) -> list[ResultadoAcceso]:
        bens = [r[0] for r in self.conn.execute(
            "SELECT id_beneficio FROM beneficios ORDER BY id_beneficio").fetchall()]
        return [self.evaluar(id_familia, b) for b in bens]


def estado_acceso_reevaluado(conn: sqlite3.Connection, id_familia: str, res,
                             fecha=FECHA_EVALUACION) -> tuple[EstadoAcceso, bool]:
    """Atajo de ``AccesoService.estado_reevaluado`` (DEC-082). Solo lectura."""
    return AccesoService(conn, fecha).estado_reevaluado(id_familia, res)


def evaluar_acceso_familia(id_familia: str, conn=None, fecha=FECHA_EVALUACION
                           ) -> list[ResultadoAcceso]:
    propia = conn is None
    conn = conn or _conn()
    try:
        return AccesoService(conn, fecha).evaluar_familia(id_familia)
    finally:
        if propia:
            conn.close()
