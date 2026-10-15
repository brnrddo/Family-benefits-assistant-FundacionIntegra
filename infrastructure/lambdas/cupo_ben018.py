"""ESBOZO — Stage reduce: cupo global de BEN-018 (Canasta Familiar).

Resuelve el ÚNICO cambio conceptual del precálculo paralelo. El cupo contingente
de BEN-018 es GLOBAL por beneficio (spec §7): se ordenan TODOS los elegibles por
inseguridad alimentaria desc, ingreso per cápita asc, id asc; las primeras
`cupo` familias entran, el resto queda `SIN_CUPO`.

En el modelo Map, ninguna partición ve el universo completo. Por eso:
  - cada `SnapshotPartitionBuilder` emite candidatos SI a S3
    (`<snapshot_id>/ben018-candidates/*.jsonl`),
  - este stage los junta, hace el ranking global y escribe el estado definitivo
    de BEN-018 por familia (`<snapshot_id>/ben018-estado.jsonl`).

Equivale exactamente a `AccesoService._familias_dentro_cupo()` del backend, pero
sobre el conjunto reunido de todas las particiones en lugar de una sola DB.

Entrada (del state): { "snapshot_id": "...", "cupo": 75 }
  `cupo` lo calcula un paso previo leyendo la versión vigente de BEN-018
  (beneficios_versiones.cupo_contingente), igual que `_cupo_ben018()`.
"""
from __future__ import annotations

import json
import os

try:
    import boto3
    _s3 = boto3.client("s3")
except Exception:  # pragma: no cover
    _s3 = None

BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
BEN_CUPO = "BEN-018"


def _leer_candidatos(snapshot_id: str) -> list[dict]:
    """Reúne todos los candidatos emitidos por las particiones del Map."""
    prefix = f"{snapshot_id}/ben018-candidates/"
    candidatos: list[dict] = []
    if _s3 and BUCKET:
        paginator = _s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                cuerpo = _s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                for linea in cuerpo.decode("utf-8").splitlines():
                    if linea.strip():
                        candidatos.append(json.loads(linea))
    else:  # local / test
        import pathlib
        base = pathlib.Path("/tmp") / prefix
        for p in base.glob("*.jsonl"):
            for linea in p.read_text(encoding="utf-8").splitlines():
                if linea.strip():
                    candidatos.append(json.loads(linea))
    return candidatos


def _rankear(candidatos: list[dict], cupo: int) -> dict[str, str]:
    """Reproduce EXACTO `AccesoService._familias_dentro_cupo` + `_derivar_estado`.

    Lógica del backend (verificada contra e3.db):
      1. Se rankean TODAS las elegibles SI (incluidas las que ya tienen gestión)
         por inseguridad DESC, ingreso_pc ASC, id ASC. Las primeras `cupo`
         están "dentro de cupo".
      2. El estado final:
         - con gestión  → su estado de gestión (ASIGNADO / GESTION_* ), ocupe o
           no cupo (la gestión manda).
         - sin gestión y dentro de cupo → ELEGIBLE_SIN_ASIGNACION.
         - sin gestión y fuera de cupo  → SIN_CUPO.

    Nota: las familias con gestión SÍ consumen posición en el ranking (están en
    el universo elegible), por eso las sin-gestión dentro de cupo son < `cupo`.
    Con e3.db esto da 45 ASIGNADO + 59 ELEGIBLE_SIN_ASIGNACION + 396 SIN_CUPO.
    """
    ordenados = sorted(
        candidatos,
        key=lambda c: (-float(c["inseguridad"]), float(c["ingreso_pc"]), c["id_familia"]),
    )
    dentro_cupo = {c["id_familia"] for c in ordenados[:cupo]}

    estado: dict[str, str] = {}
    for c in candidatos:
        fam = c["id_familia"]
        if c.get("tiene_gestion"):
            estado[fam] = c["estado_gestion"]          # la gestión manda
        elif fam in dentro_cupo:
            estado[fam] = "ELEGIBLE_SIN_ASIGNACION"
        else:
            estado[fam] = "SIN_CUPO"
    return estado


def _put_jsonl(key: str, registros: list[dict]) -> None:
    cuerpo = "\n".join(json.dumps(r, ensure_ascii=False) for r in registros)
    if _s3 and BUCKET:
        _s3.put_object(Bucket=BUCKET, Key=key, Body=cuerpo.encode("utf-8"))
    else:
        import pathlib
        p = pathlib.Path("/tmp") / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo, encoding="utf-8")


def handler(event: dict, _context=None) -> dict:
    snapshot_id = event["snapshot_id"]
    cupo = int(event["cupo"])

    candidatos = _leer_candidatos(snapshot_id)
    estado = _rankear(candidatos, cupo)

    filas = [
        {"id_familia": fam, "id_beneficio": BEN_CUPO, "estado": est}
        for fam, est in estado.items()
    ]
    _put_jsonl(f"{snapshot_id}/ben018-estado.jsonl", filas)

    return {
        "candidatos": len(candidatos),
        "cupo": cupo,
        "dentro_cupo": sum(1 for v in estado.values() if v != "SIN_CUPO"),
        "sin_cupo": sum(1 for v in estado.values() if v == "SIN_CUPO"),
    }
