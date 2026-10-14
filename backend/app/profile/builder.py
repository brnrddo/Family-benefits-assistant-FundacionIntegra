"""Constructor del perfil consolidado de familia."""
from __future__ import annotations

import sqlite3

from ..access.model import EstadoAcceso
from ..access.service import AccesoService
from ..config import DB_PATH, FECHA_EVALUACION
from ..engine.facts import Repo
from ..engine.model import Nivel, Tri

# Beneficios cuya elegibilidad NO es determinable solo con los datos públicos
# (dependen de datos externos ausentes o del cruce de accesos — ver M2/M3).
# Si el motor da INDETERMINADO por falta de dato externo, caen aquí.
#
# El perfil clasifica cada beneficio en 4 grupos según el resultado del motor:
#   - elegible_determinable : SI (con dato observado o supuesto declarado)
#   - candidato             : INDETERMINADO por un dato que la familia PODRÍA acreditar
#   - no_evaluable          : INDETERMINADO por un dato externo que no depende de la familia
#   - (NO)                  : no aplica, se omite del contexto de recomendación
#
# Campos faltantes que dependen de un dato EXTERNO (no acreditable por la familia
# en una conversación simple) -> clasifican el beneficio como "no_evaluable".
DATOS_EXTERNOS = {
    # dependen de datos clínicos/externos que la familia no acredita conversando
    "parto_red_publica",
    "control_prenatal_red_publica",
    "documento_terapia_dias",
    "distancia_terapia_km",
    "terapia_vigencia",
    "dias_desde_evento",
    "pago_previo_ben020",
    # dependen del cruce de ACCESO/gestiones (no de un documento de la familia)
    "estado_acceso",
    "id_beneficio_o_programa",
    "vigencia",
    "carga_acreditada_de",
}


def _conn(db_path=None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _val(row, key, default=None):
    try:
        v = row[key]
        return v if v not in (None, "") else default
    except (IndexError, KeyError):
        return default


class ProfileBuilder:
    def __init__(self, conn: sqlite3.Connection, fecha: str = FECHA_EVALUACION):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.fecha = fecha
        self.repo = Repo(conn, fecha)
        self.acceso = AccesoService(conn, fecha)

    # --- secciones -----------------------------------------------------------
    def _identidad(self, fam) -> dict:
        jardin = self.conn.execute(
            "SELECT * FROM jardines WHERE id_jardin = ?", (fam["id_jardin"],)
        ).fetchone()
        comuna = self.conn.execute(
            "SELECT * FROM comunas WHERE id_comuna = ?",
            (fam["id_comuna_residencia_corte"],)
        ).fetchone()
        return {
            "id_familia": fam["id_familia"],
            "id_jardin": fam["id_jardin"],
            "comuna": fam["id_comuna_residencia_corte"],
            "comuna_nombre": _val(comuna, "nombre_comuna_sintetico") if comuna else None,
            "region": fam["region_codigo_residencia_corte"],
            "tipo_zona": _val(jardin, "tipo_zona") if jardin else None,
        }

    def _rsh(self, fam) -> dict:
        tramo = _val(fam, "tramo_rsh_corte")
        hist = self.conn.execute(
            "SELECT * FROM rsh_historial WHERE id_familia = ?", (fam["id_familia"],)
        ).fetchall()
        vigente = None
        for h in hist:
            if Repo._vig(h["vigencia_desde"], h["vigencia_hasta"], self.fecha):
                vigente = h
                break
        return {
            "estado_rsh": _val(fam, "estado_rsh_corte"),
            "tramo_rsh": int(tramo) if tramo and str(tramo).isdigit() else tramo,
            "subtramo": _val(vigente, "subtramo_sintetico") if vigente else None,
            "vigencia_desde": _val(vigente, "vigencia_desde") if vigente else None,
            "vigencia_hasta": _val(vigente, "vigencia_hasta") if vigente else None,
            "rsh_conocido": tramo is not None,
        }

    def _composicion(self, fam) -> dict:
        ints = self.repo.integrantes(fam["id_familia"])
        integrantes = []
        ninos_jardin = []
        persona_ref = None
        for i in ints:
            edad = self.repo.edad_anios(i["fecha_nacimiento_sintetica"])
            es_nino = str(_val(i, "es_nino_jardin", "false")).lower() == "true"
            item = {
                "id_integrante": i["id_integrante"],
                "edad": edad,
                "parentesco": _val(i, "parentesco"),
                "es_nino_jardin": es_nino,
                "sexo": _val(i, "sexo_registral_sintetico"),
            }
            integrantes.append(item)
            if i["parentesco"] == "PERSONA_REFERENCIA" and persona_ref is None:
                persona_ref = item
            if es_nino:
                ninos_jardin.append({**item, **self._matricula_nino(i["id_integrante"])})
        return {
            "numero_integrantes": _val(fam, "numero_integrantes_corte"),
            "integrantes": integrantes,
            "ninos_jardin": ninos_jardin,
            "persona_referencia": persona_ref,
        }

    def _matricula_nino(self, id_integrante: str) -> dict:
        rows = self.conn.execute(
            "SELECT subtipo, valor_texto FROM condiciones_integrante "
            "WHERE id_integrante = ? AND tipo_condicion = 'MATRICULA'", (id_integrante,)
        ).fetchall()
        m = {r["subtipo"]: r["valor_texto"] for r in rows}
        return {
            "matricula_estado": m.get("ESTADO"),
            "nivel": m.get("NIVEL"),
            "tipo_establecimiento": m.get("TIPO_ESTABLECIMIENTO"),
        }

    def _antecedentes(self, fam) -> dict:
        fid = fam["id_familia"]
        ingreso = self._eav_hogar(fid, "INGRESO_HOGAR", "MONTO")
        residencia = self._eav_hogar(fid, "RESIDENCIA", "COMUNA")
        # Condiciones relevantes por integrante (con flag de acreditación).
        condiciones = []
        rel = ("DISCAPACIDAD", "MATRICULA", "CONTROL_SALUD", "TERAPIA", "PREVISION")
        for i in self.repo.integrantes(fid):
            rows = self.conn.execute(
                "SELECT * FROM condiciones_integrante WHERE id_integrante = ? "
                "AND tipo_condicion IN (%s)" % ",".join("?" * len(rel)),
                (i["id_integrante"], *rel)
            ).fetchall()
            for r in rows:
                if not Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                    continue
                condiciones.append({
                    "id_integrante": i["id_integrante"],
                    "tipo": r["tipo_condicion"],
                    "subtipo": r["subtipo"],
                    "valor": self._valor_eav(r),
                    "acreditada": str(_val(r, "acreditada", "false")).lower() == "true",
                    "estado_dato": _val(r, "estado_dato"),
                })
        return {
            "ingreso_hogar": ingreso,
            "residencia": residencia,
            "condiciones": condiciones,
        }

    def _eav_hogar(self, fid, tipo, subtipo):
        rows = self.conn.execute(
            "SELECT * FROM antecedentes_familia WHERE id_familia = ? AND tipo_antecedente = ? "
            "AND subtipo = ?", (fid, tipo, subtipo)
        ).fetchall()
        for r in rows:
            if Repo._vig(r["vigencia_desde"], r["vigencia_hasta"], self.fecha):
                return self._valor_eav(r)
        return None

    @staticmethod
    def _valor_eav(r):
        for col in ("valor_numero", "valor_texto", "valor_booleano", "valor_fecha"):
            if r[col] not in (None, ""):
                v = r[col]
                if col == "valor_numero":
                    try:
                        return int(v) if "." not in str(v) else float(v)
                    except ValueError:
                        return v
                if col == "valor_booleano":
                    return str(v).lower() == "true"
                return v
        return None

    def _historial(self, fam) -> dict:
        fid = fam["id_familia"]
        accesos = self.conn.execute(
            "SELECT id_beneficio_o_programa, estado_acceso, vigencia_desde, vigencia_hasta "
            "FROM accesos_previos_hogar WHERE id_familia = ?", (fid,)
        ).fetchall()
        accesos_previos = [{
            "beneficio": a["id_beneficio_o_programa"],
            "estado": a["estado_acceso"],
            "vigencia_desde": a["vigencia_desde"],
            "vigencia_hasta": a["vigencia_hasta"],
        } for a in accesos]

        posts = self.conn.execute(
            "SELECT id_postulacion, id_beneficio FROM postulaciones WHERE id_familia = ?",
            (fid,)
        ).fetchall()
        postulaciones = []
        for p in posts:
            ult = self.conn.execute(
                "SELECT estado FROM postulaciones_estados WHERE id_postulacion = ? "
                "ORDER BY CAST(secuencia AS INTEGER) DESC LIMIT 1", (p["id_postulacion"],)
            ).fetchone()
            postulaciones.append({
                "id_postulacion": p["id_postulacion"],
                "beneficio": p["id_beneficio"],
                "ultimo_estado": ult[0] if ult else None,
            })
        return {
            "accesos_previos": accesos_previos,
            "postulaciones": postulaciones,
        }

    def _contexto_recomendacion(self, id_familia: str) -> dict:
        """Clasifica los 20 beneficios en los 4 grupos derivados."""
        elegibles, candidatos, no_evaluables = [], [], []
        datos_faltantes: set[str] = set()

        for acc in self.acceso.evaluar_familia(id_familia):
            elig = acc.elegibilidad
            ben = acc.id_beneficio
            resultado = elig.get("resultado")
            faltan = elig.get("datos_faltantes", [])

            if resultado == Tri.SI.value:
                elegibles.append({
                    "beneficio": ben,
                    "estado_acceso": acc.estado.value,
                    "preliminar": acc.preliminar,
                    "monto_estimado": elig.get("monto_estimado"),
                })
            elif resultado == Tri.INDETERMINADO.value:
                es_externo = any(f in DATOS_EXTERNOS for f in faltan)
                destino = no_evaluables if es_externo else candidatos
                destino.append({
                    "beneficio": ben,
                    "datos_faltantes": faltan,
                })
                datos_faltantes.update(faltan)
            # NO -> se omite del contexto de recomendación

        return {
            "beneficios_elegibles_determinables": elegibles,
            "beneficios_candidatos": candidatos,
            "beneficios_no_evaluables": no_evaluables,
            "datos_faltantes": sorted(datos_faltantes),
        }

    # --- perfil completo -----------------------------------------------------
    def build(self, id_familia: str) -> dict | None:
        fam = self.repo.familia(id_familia)
        if fam is None:
            return None
        return {
            "identidad": self._identidad(fam),
            "rsh": self._rsh(fam),
            "composicion": self._composicion(fam),
            "antecedentes": self._antecedentes(fam),
            "historial": self._historial(fam),
            "contexto_recomendacion": self._contexto_recomendacion(id_familia),
        }


def construir_perfil(id_familia: str, conn=None, fecha=FECHA_EVALUACION) -> dict | None:
    propia = conn is None
    conn = conn or _conn()
    try:
        return ProfileBuilder(conn, fecha).build(id_familia)
    finally:
        if propia:
            conn.close()
