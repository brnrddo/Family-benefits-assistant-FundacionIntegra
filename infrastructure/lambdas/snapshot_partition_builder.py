"""ESBOZO — Lambda `SnapshotPartitionBuilder` (un jardín por invocación).

Wrapper FINO sobre el código existente del backend. NO reimplementa el motor:
reutiliza `AccesoService.evaluar_familia`. Cada child execution del Distributed
Map llama a este handler con un jardín y escribe su partición a S3.

Contrato de entrada (lo pone el Map desde el manifiesto en S3):
    {
        "snapshot_id": "2026-10-15T12:00:00Z",
        "jardin_id":   "JARDIN-SIM-E3-017",
        "fecha_evaluacion": "2026-10-13"      # opcional; default config
    }

Salida (escrita a S3, no devuelta por payload para no chocar con 256 KB):
    s3://<BUCKET>/<snapshot_id>/partitions/<jardin_id>.jsonl
        → una línea JSON por (familia, beneficio) EXCEPTO BEN-018
    s3://<BUCKET>/<snapshot_id>/ben018-candidates/<jardin_id>.jsonl
        → candidatos de BEN-018 (SI) con llaves de orden, para el reduce global

Empaquetado: el backend es stdlib + sqlite3; sube `backend/app` como código de
la Lambda (o layer). `e3.db` viaja de solo-lectura en la imagen/layer, o se
materializa por jardín. Para el esbozo asumimos `e3.db` disponible en /opt o /tmp.

Cambio conceptual clave: este builder NO decide SIN_CUPO. Para BEN-018 solo
emite candidatos; el ranking global lo hace `cupo_ben018.py` (stage aparte),
porque el cupo es por beneficio sobre todo el universo, no por jardín.
"""
from __future__ import annotations

import json
import os
import sqlite3

# --- dependencias del propio backend (reutilizadas, no reescritas) -----------
# En la Lambda, `app` está en el PYTHONPATH (código subido o layer).
from app.access.service import AccesoService, BEN_CUPO
from app.engine.model import Tri

# boto3 está en el runtime de Lambda; import perezoso para tests locales.
try:
    import boto3
    _s3 = boto3.client("s3")
except Exception:  # pragma: no cover - entorno local sin boto3
    _s3 = None

BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
DB_PATH = os.environ.get("E3_DB_PATH", "/opt/e3.db")  # solo-lectura


def _conn() -> sqlite3.Connection:
    # uri=True + mode=ro: abre la base de solo-lectura (varias Lambdas en paralelo
    # leen la misma copia sin riesgo de escritura concurrente).
    c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _familias_de_jardin(conn: sqlite3.Connection, jardin_id: str) -> list[str]:
    """Familias cuyo hogar pertenece al jardín dado.

    Columna verificada contra data/publico/familias.csv: `familias.id_jardin`
    (valores tipo `JAR-SIM-E3-00001`).
    """
    rows = conn.execute(
        "SELECT id_familia FROM familias WHERE id_jardin = ? ORDER BY id_familia",
        (jardin_id,),
    ).fetchall()
    return [r[0] for r in rows]


def _candidato_ben018(svc: AccesoService, id_familia: str) -> dict | None:
    """Si la familia es SI en BEN-018, devuelve sus llaves de orden global.

    Reutiliza helpers YA EXISTENTES de AccesoService (inseguridad, ingreso,
    última postulación/estado). El corte en `cupo` NO se hace aquí (eso es
    global → stage reduce). También emite `tiene_gestion`/`estado_gestion` para
    que el reduce reproduzca EXACTO el backend: solo las SI sin gestión compiten
    por el cupo; las que ya tienen gestión conservan su estado (ASIGNADO, etc.).
    """
    elig = svc.ev.evaluar(id_familia, BEN_CUPO)
    if elig.resultado != Tri.SI:
        return None
    inseguridad = svc._eav_hogar_num(id_familia, "INSEGURIDAD_ALIMENTARIA", "INDICE") or 0.0
    ingreso = svc._eav_hogar_num(id_familia, "INGRESO_HOGAR", "MONTO")
    n = conn_numero_integrantes(svc.conn, id_familia)
    try:
        pc = (ingreso / float(n)) if (ingreso is not None and n) else float("inf")
    except (ValueError, TypeError, ZeroDivisionError):
        pc = float("inf")

    # Estado de gestión (misma lógica que AccesoService.evaluar para BEN-018).
    post = svc._ultima_postulacion(id_familia, BEN_CUPO)
    tiene_gestion = post is not None
    estado_gestion = None
    if tiene_gestion:
        ultimo = svc._ultimo_estado(post["id_postulacion"])
        if ultimo == "VIGENTE":
            estado_gestion = "ASIGNADO"
        elif ultimo == "RECHAZADA":
            estado_gestion = "GESTION_RECHAZADA"
        else:
            estado_gestion = "GESTION_EN_CURSO"

    return {
        "id_familia": id_familia,
        "inseguridad": inseguridad,   # orden DESC
        "ingreso_pc": pc,             # orden ASC
        "tiene_gestion": tiene_gestion,
        "estado_gestion": estado_gestion,
    }


def conn_numero_integrantes(conn: sqlite3.Connection, id_familia: str) -> int:
    row = conn.execute(
        "SELECT numero_integrantes_corte FROM familias WHERE id_familia = ?",
        (id_familia,),
    ).fetchone()
    return int(row[0]) if row and row[0] not in (None, "") else 0


def _put_jsonl(key: str, registros: list[dict]) -> None:
    """Escribe una lista de dicts como JSONL a S3 (o a /tmp en local)."""
    cuerpo = "\n".join(json.dumps(r, ensure_ascii=False) for r in registros)
    if _s3 and BUCKET:
        _s3.put_object(Bucket=BUCKET, Key=key, Body=cuerpo.encode("utf-8"))
    else:  # local / test: dejar en /tmp para inspección
        import pathlib
        p = pathlib.Path("/tmp") / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo, encoding="utf-8")


def handler(event: dict, _context=None) -> dict:
    """Entry point de la Lambda (un jardín)."""
    snapshot_id = event["snapshot_id"]
    jardin_id = event["jardin_id"]
    fecha = event.get("fecha_evaluacion")  # None → default de config

    conn = _conn()
    try:
        svc = AccesoService(conn, fecha) if fecha else AccesoService(conn)
        familias = _familias_de_jardin(conn, jardin_id)

        filas: list[dict] = []
        candidatos018: list[dict] = []

        for fam in familias:
            # Reutiliza el M3 completo tal cual; filtramos BEN-018 del resultado
            # porque su estado (SIN_CUPO) depende del ranking global.
            for acc in svc.evaluar_familia(fam):
                if acc.id_beneficio == BEN_CUPO:
                    continue
                filas.append(acc.to_dict())   # contrato C1/estado ya definido
            cand = _candidato_ben018(svc, fam)
            if cand is not None:
                candidatos018.append(cand)

        _put_jsonl(f"{snapshot_id}/partitions/{jardin_id}.jsonl", filas)
        _put_jsonl(f"{snapshot_id}/ben018-candidates/{jardin_id}.jsonl", candidatos018)

        return {
            "jardin_id": jardin_id,
            "familias": len(familias),
            "filas": len(filas),
            "candidatos_ben018": len(candidatos018),
        }
    finally:
        conn.close()


if __name__ == "__main__":  # smoke local
    print(handler({"snapshot_id": "local-test", "jardin_id": "JARDIN-SIM-E3-001"}))
