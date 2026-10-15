"""Carga y validación del bundle C4 para el ranking determinista U/B/V (FEAT-001).

Autoridad: el bundle C4 (`content/manifest.json`) es la única fuente de todos los
números de negocio de §8. Este módulo NO contiene umbrales/pesos/medianas/bonus
hardcodeados: solo carga, valida y expone la configuración.

Falla cerrado: cualquier bundle inválido (schema o invariantes de negocio) lanza
``ConfigInvalida`` y nada downstream debe continuar con una config dudosa.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import jsonschema

# Raíz del repo: .../Aws-breaking-barriers---10-  (backend/app/priority -> repo)
_REPO_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Schema cerrado C4 (solo lectura; autoridad de contratos).
_C4_SCHEMA_PATH = (
    _REPO_DIR
    / ".kiro"
    / "specs"
    / "_shared"
    / "contracts"
    / "C4-contenido-manifest.schema.json"
)

# Ruta por defecto del manifest; configurable por entorno (E3_CONTENT_MANIFEST).
_DEFAULT_MANIFEST = _REPO_DIR / "content" / "manifest.json"

# Tolerancia de la suma de ejes U/B/V (contrato C4: 1 ± 1e-6).
AXIS_SUM_TOLERANCE = 1e-6


class ConfigInvalida(Exception):
    """El bundle C4 no cumple schema o invariantes de negocio: falla cerrado."""


@dataclass(frozen=True)
class RankingConfig:
    """Vista tipada de solo lectura del bloque ``ranking`` + ``kpi``/``accessibility``.

    Cada bloque se expone tal cual viene del bundle validado. No se derivan ni
    recalculan números aquí: scoring los consume directamente.
    """

    axis_weights: dict
    urgency: dict
    benefit_impact: dict
    vulnerability: dict
    opportunity_score: dict
    family_priority: dict
    kpi: dict
    accessibility: dict
    content_version: str
    content_bundle_hash: str

    def garden_income_median(self, garden_id: str | None) -> float:
        """Mediana de ingreso del jardín, o el default si no hay dato por jardín."""
        medians = self.benefit_impact["garden_income_medians"]
        if garden_id is not None:
            for entry in medians:
                if entry["garden_id"] == garden_id:
                    return float(entry["monthly_household_income"])
        return float(self.benefit_impact["default_monthly_household_income"])

    def service_equivalence(self, benefit_id: str) -> float | None:
        """Monto anual equivalente para un servicio, si está declarado."""
        for entry in self.benefit_impact["service_equivalences"]:
            if entry["benefit_id"] == benefit_id:
                return float(entry["annual_equivalent_amount"])
        return None


def _load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise ConfigInvalida(f"No se encontró el bundle C4 en {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigInvalida(f"Bundle C4 no es JSON válido: {exc}") from exc


def _validar_invariantes_negocio(manifest: dict) -> None:
    """Valida invariantes que el schema cerrado no cubre; falla cerrado."""
    ranking = manifest["ranking"]

    # 1) Suma de ejes U/B/V == 1 ± tolerancia.
    aw = ranking["axis_weights"]
    suma = aw["u"] + aw["b"] + aw["v"]
    if abs(suma - 1.0) > AXIS_SUM_TOLERANCE:
        raise ConfigInvalida(
            f"axis_weights u+b+v debe sumar 1 (±{AXIS_SUM_TOLERANCE}); suma={suma}"
        )

    # 2) Debe existir un default de ingreso del hogar (fallback de mediana).
    bi = ranking["benefit_impact"]
    default_income = bi.get("default_monthly_household_income")
    if not default_income or default_income <= 0:
        raise ConfigInvalida(
            "benefit_impact.default_monthly_household_income ausente o no positivo: "
            "sin él no hay mediana de respaldo para calcular B"
        )


def cargar_ranking_config(manifest_path: str | os.PathLike | None = None) -> RankingConfig:
    """Carga el bundle C4, valida schema + invariantes y devuelve ``RankingConfig``.

    La ruta se resuelve en este orden: argumento explícito > variable de entorno
    ``E3_CONTENT_MANIFEST`` > ``content/manifest.json`` del repo.
    """
    if manifest_path is None:
        env = os.environ.get("E3_CONTENT_MANIFEST")
        path = Path(env) if env else _DEFAULT_MANIFEST
    else:
        path = Path(manifest_path)

    manifest = _load_json(path)
    schema = _load_json(_C4_SCHEMA_PATH)

    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as exc:
        raise ConfigInvalida(f"Bundle C4 no cumple el schema cerrado: {exc.message}") from exc

    _validar_invariantes_negocio(manifest)

    ranking = manifest["ranking"]
    return RankingConfig(
        axis_weights=ranking["axis_weights"],
        urgency=ranking["urgency"],
        benefit_impact=ranking["benefit_impact"],
        vulnerability=ranking["vulnerability"],
        opportunity_score=ranking["opportunity_score"],
        family_priority=ranking["family_priority"],
        kpi=manifest["kpi"],
        accessibility=manifest["accessibility"],
        content_version=manifest["content_version"],
        content_bundle_hash=manifest["content_bundle_hash"],
    )
