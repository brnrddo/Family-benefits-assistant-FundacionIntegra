"""ESBOZO — Prepara el manifiesto de jardines para el Distributed Map.

El Distributed Map itera sobre ítems leídos de S3 (JSONL), NO sobre un array
embebido en el estado (así se evita el límite de 256 KB). Este stage genera ese
manifiesto: una línea por jardín.

Salida: s3://<BUCKET>/<snapshot_id>/manifest/jardines.jsonl
    {"snapshot_id": "...", "jardin_id": "JARDIN-SIM-E3-001", "fecha_evaluacion": "..."}
    {"snapshot_id": "...", "jardin_id": "JARDIN-SIM-E3-002", "fecha_evaluacion": "..."}
    ...
"""
from __future__ import annotations

import json
import os
import sqlite3

try:
    import boto3
    _s3 = boto3.client("s3")
except Exception:  # pragma: no cover
    _s3 = None

BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
DB_PATH = os.environ.get("E3_DB_PATH", "/opt/e3.db")


def _jardines(fecha: str | None) -> list[str]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT DISTINCT id_jardin FROM familias "
            "WHERE id_jardin IS NOT NULL ORDER BY id_jardin"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def handler(event: dict, _context=None) -> dict:
    snapshot_id = event["snapshot_id"]
    fecha = event.get("fecha_evaluacion")

    jardines = _jardines(fecha)
    lineas = [
        json.dumps(
            {"snapshot_id": snapshot_id, "jardin_id": j, "fecha_evaluacion": fecha},
            ensure_ascii=False,
        )
        for j in jardines
    ]
    key = f"{snapshot_id}/manifest/jardines.jsonl"
    cuerpo = "\n".join(lineas).encode("utf-8")

    if _s3 and BUCKET:
        _s3.put_object(Bucket=BUCKET, Key=key, Body=cuerpo)

    # El Map leerá este objeto como ItemReader (ver precompute_stack.py).
    return {
        "snapshot_id": snapshot_id,
        "manifest_bucket": BUCKET,
        "manifest_key": key,
        "jardines": len(jardines),
    }
