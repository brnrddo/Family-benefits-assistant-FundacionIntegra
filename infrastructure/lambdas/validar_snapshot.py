"""ESBOZO — Validación + smoke test + activación transaccional de CONTROL/ACTIVE.

Último stage del pipeline. Reúne lo que escribieron el Map (particiones por
jardín, sin BEN-018) y el reduce (estado de BEN-018), valida el snapshot y, si
pasa, lo activa reemplazando los SEIS campos de CONTROL/ACTIVE en DynamoDB con
una transacción condicional (spec ARQUITECTURA_AWS §"Datos, activación y fallos").

Garantías del diseño que este stage implementa:
  - El snapshot activo anterior se conserva intacto si la validación falla.
  - La activación es transaccional: reemplaza exactamente snapshot_id,
    eligibility_bundle_hash, content_bundle_hash, content_version, published_at,
    generation.
  - Carrera: si otra ejecución activó una generación mayor, la condición falla
    y este snapshot queda SUPERSEDED (no pisa el activo).

Entrada:  { "snapshot_id": "...", "ben018": {...}, "cupo": {...} }
Salida:   { "activated": true|false, "snapshot_id": "...", "reason": "..." }
"""
from __future__ import annotations

import hashlib
import json
import os
import time

try:
    import boto3
    _s3 = boto3.client("s3")
    _ddb = boto3.client("dynamodb")
except Exception:  # pragma: no cover
    _s3 = _ddb = None

BUCKET = os.environ.get("SNAPSHOT_BUCKET", "")
CONTROL_TABLE = os.environ.get("CONTROL_TABLE", "")
CONTROL_PK = "CONTROL#ACTIVE"

# Umbrales esperados (plan Rol 1). Ajustar si cambia el dataset.
FAMILIAS_ESPERADAS = 500
BENEFICIOS = 20
# Evaluaciones = 500 x 20. En S3 están 19 por familia (BEN-018 va en su JSONL).
FILAS_SIN_018_ESPERADAS = FAMILIAS_ESPERADAS * (BENEFICIOS - 1)


# --- lectura de lo producido por los stages previos -------------------------
def _leer_jsonl_prefijo(prefix: str) -> list[dict]:
    registros: list[dict] = []
    if _s3 and BUCKET:
        paginator = _s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                cuerpo = _s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                for linea in cuerpo.decode("utf-8").splitlines():
                    if linea.strip():
                        registros.append(json.loads(linea))
    else:  # local / test
        import pathlib
        base = pathlib.Path("/tmp") / prefix
        if base.exists():
            for p in base.glob("*.jsonl"):
                for linea in p.read_text(encoding="utf-8").splitlines():
                    if linea.strip():
                        registros.append(json.loads(linea))
    return registros


def _leer_jsonl_objeto(key: str) -> list[dict]:
    registros: list[dict] = []
    if _s3 and BUCKET:
        cuerpo = _s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    else:
        import pathlib
        p = pathlib.Path("/tmp") / key
        cuerpo = p.read_bytes() if p.exists() else b""
    for linea in cuerpo.decode("utf-8").splitlines():
        if linea.strip():
            registros.append(json.loads(linea))
    return registros


def _hash(registros: list[dict]) -> str:
    """Hash estable del bundle (orden-independiente)."""
    firmas = sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in registros)
    h = hashlib.sha256()
    for f in firmas:
        h.update(f.encode("utf-8"))
    return h.hexdigest()


# --- validación -------------------------------------------------------------
def _validar(particiones: list[dict], ben018: list[dict]) -> tuple[bool, str]:
    if not particiones:
        return False, "sin particiones"
    # Conteo de filas de elegibilidad/estado (sin BEN-018).
    if len(particiones) != FILAS_SIN_018_ESPERADAS:
        return False, (f"filas sin BEN-018 = {len(particiones)}, "
                       f"esperado {FILAS_SIN_018_ESPERADAS}")
    # BEN-018: una fila por familia elegible candidata (<= 500).
    if len(ben018) > FAMILIAS_ESPERADAS:
        return False, f"ben018 con {len(ben018)} filas (> {FAMILIAS_ESPERADAS})"
    # Smoke test mínimo: cada fila trae estado y par (familia, beneficio).
    for r in particiones[:50]:
        if not r.get("id_familia") or not r.get("id_beneficio") or not r.get("estado"):
            return False, "fila incompleta en smoke test"
    return True, "ok"


# --- activación transaccional ----------------------------------------------
def _generacion_actual() -> int:
    if not (_ddb and CONTROL_TABLE):
        return 0
    resp = _ddb.get_item(
        TableName=CONTROL_TABLE,
        Key={"pk": {"S": CONTROL_PK}},
        ConsistentRead=True,
    )
    item = resp.get("Item")
    return int(item["generation"]["N"]) if item and "generation" in item else 0


def _activar(snapshot_id: str, elig_hash: str, content_hash: str,
             content_version: str, generacion_nueva: int) -> tuple[bool, str]:
    """Reemplazo condicional de los seis campos. Falla cerrada ante carrera."""
    if not (_ddb and CONTROL_TABLE):
        return True, "local (sin DynamoDB): activación simulada"
    try:
        _ddb.put_item(
            TableName=CONTROL_TABLE,
            Item={
                "pk": {"S": CONTROL_PK},
                "snapshot_id": {"S": snapshot_id},
                "eligibility_bundle_hash": {"S": elig_hash},
                "content_bundle_hash": {"S": content_hash},
                "content_version": {"S": content_version},
                "published_at": {"S": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                "generation": {"N": str(generacion_nueva)},
            },
            # Solo activa si nadie subió la generación mientras tanto.
            ConditionExpression="attribute_not_exists(pk) OR generation < :g",
            ExpressionAttributeValues={":g": {"N": str(generacion_nueva)}},
        )
        return True, "activado"
    except _ddb.exceptions.ConditionalCheckFailedException:
        return False, "SUPERSEDED (otra generación activó primero)"


def handler(event: dict, _context=None) -> dict:
    snapshot_id = event["snapshot_id"]

    particiones = _leer_jsonl_prefijo(f"{snapshot_id}/partitions/")
    ben018 = _leer_jsonl_objeto(f"{snapshot_id}/ben018-estado.jsonl")

    ok, motivo = _validar(particiones, ben018)
    if not ok:
        # No se toca el activo anterior.
        return {"activated": False, "snapshot_id": snapshot_id, "reason": motivo}

    elig_hash = _hash(particiones + ben018)
    content_hash = _hash([])  # ESBOZO: hash del content bundle (C4), cuando exista
    content_version = str(event.get("content_version", "v1"))
    generacion_nueva = _generacion_actual() + 1

    activado, motivo = _activar(
        snapshot_id, elig_hash, content_hash, content_version, generacion_nueva)
    return {
        "activated": activado,
        "snapshot_id": snapshot_id,
        "reason": motivo,
        "eligibility_bundle_hash": elig_hash,
        "generation": generacion_nueva,
    }
