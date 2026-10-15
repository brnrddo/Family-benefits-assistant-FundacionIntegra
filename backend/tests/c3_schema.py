"""Validación contra el contrato C3 (helper de tests; no es un test).

Mismo patrón que ``_schema_validator``/``_validar``/``_validar_error`` de
``test_api_mocks.py`` (que no se modifica): el schema se carga del YAML de C3
sin editarlo y los ``$ref`` externos se resuelven contra el disco. Los
validadores se cachean por nombre para poder recorrer las 500 familias.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

_REPO_DIR = Path(__file__).resolve().parent.parent.parent
_CONTRACTS_DIR = _REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
_C3_PATH = _CONTRACTS_DIR / "C3-api.openapi.yaml"


@lru_cache(maxsize=1)
def cargar_c3() -> dict:
    with _C3_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=None)
def _validador(nombre: str) -> Draft202012Validator:
    c3 = cargar_c3()
    base_uri = _CONTRACTS_DIR.as_uri() + "/"

    def _handler(uri: str) -> dict:
        path = Path(uri[len("file:///"):]) if uri.startswith("file:///") else Path(uri)
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    resolver = RefResolver(base_uri=base_uri, referrer=c3, handlers={"file": _handler})
    return Draft202012Validator({"$ref": f"#/components/schemas/{nombre}"}, resolver=resolver)


def validar(nombre: str, payload: dict) -> None:
    """Falla con los mensajes del schema (nunca con los valores) si no cumple."""
    errores = sorted(_validador(nombre).iter_errors(payload), key=lambda e: list(e.path))
    assert not errores, f"{nombre}: " + "; ".join(
        f"{'/'.join(str(p) for p in e.path)} {e.validator}" for e in errores
    )


@lru_cache(maxsize=1)
def _validador_error() -> Draft202012Validator:
    with (_CONTRACTS_DIR / "schemas" / "ErrorResponse.schema.json").open(encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def validar_error(payload: dict) -> None:
    _validador_error().validate(payload)
    # Nunca ecoa PII: el mensaje es un texto fijo genérico.
    assert "nombre" not in json.dumps(payload).lower()
