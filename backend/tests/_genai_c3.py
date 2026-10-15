"""Helper de validación C3 para los tests del catálogo GenAI (no lo recoge pytest).

Mismo patrón que ``test_api_mocks._schema_validator``: valida contra
``#/components/schemas/<nombre>`` del YAML de C3, resolviendo los ``$ref``
internos contra el documento y los externos (``./schemas/*.json``) en disco.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

REPO_DIR = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
_C3_PATH = CONTRACTS_DIR / "C3-api.openapi.yaml"
_ERROR_PATH = CONTRACTS_DIR / "schemas" / "ErrorResponse.schema.json"


@lru_cache(maxsize=1)
def _c3() -> dict:
    with _C3_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _handler(uri: str) -> dict:
    path = Path(uri[len("file:///"):]) if uri.startswith("file:///") else Path(uri)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def _validator(nombre: str) -> Draft202012Validator:
    resolver = RefResolver(
        base_uri=CONTRACTS_DIR.as_uri() + "/",
        referrer=_c3(),
        handlers={"file": _handler},
    )
    return Draft202012Validator({"$ref": f"#/components/schemas/{nombre}"}, resolver=resolver)


def validar(nombre: str, payload: dict) -> None:
    """Falla con los mensajes de error si ``payload`` no cumple el schema C3."""
    errores = sorted(_validator(nombre).iter_errors(payload), key=lambda e: list(e.path))
    assert not errores, f"{nombre}: " + "; ".join(e.message for e in errores)


def validar_error(payload: dict) -> None:
    """Valida contra ``ErrorResponse.schema.json``."""
    with _ERROR_PATH.open(encoding="utf-8") as fh:
        Draft202012Validator(json.load(fh)).validate(payload)
