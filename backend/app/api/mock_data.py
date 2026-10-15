"""Fixtures sintéticos deterministas para los 12 flujos C3 (FEAT-003).

TODO el contenido es 100% sintético, rotulado y CONSTANTE: los mismos IDs y
conteos en cada corrida. Las oportunidades respetan las invariantes ``oneOf``
de C3 (se validan al construir con ``validar_opportunity``). Nada describe a una
persona real; los objetos de persona/hogar llevan ``data_classification``
``SYNTHETIC_DEMO_NOT_A_REAL_PERSON`` donde el schema lo admite (preevaluación).

Las respuestas de guion/mensaje/asistente NO se arman aquí: las produce el
``TemplateProvider`` de FEAT-002 desde el catálogo C4 (ver ``runtime``).
"""
from __future__ import annotations

from app.api.deps import DISCLAIMER
from app.api.models import validar_benefit_result, validar_opportunity

# Fuente de cita HTTPS inventariada (coincide con el bundle C4 provisional).
_SOURCE = {"source_id": "SRC-OFICIAL", "url": "https://www.chileatiende.gob.cl/"}


# --- Jardines (listJardines) -------------------------------------------------

JARDINES: list[dict] = [
    {
        "garden_id": "JARDIN-001",
        "commune_id": "COM-001",
        "region_id": "REG-001",
        "zone": "URBANA",
        "families_total": 42,
        "families_informed": 18,
        "informed_percentage": 42.9,
    },
    {
        "garden_id": "JARDIN-002",
        "commune_id": "COM-002",
        "region_id": "REG-001",
        "zone": "RURAL",
        "families_total": 27,
        "families_informed": 9,
        "informed_percentage": 33.3,
    },
]

_GARDEN_IDS = {j["garden_id"] for j in JARDINES}


# --- Oportunidades sintéticas (coherentes con el oneOf) ----------------------


def _opp(
    benefit_id: str,
    simple_title: str,
    result: str,
    level: str | None,
    access_state: str,
    urgency: float,
    benefit: float,
    vulnerability: float,
    score: float,
    position: int,
    estimated_annual_amount: float | None,
    benefit_estimated: bool,
    action_type: str,
    why_first: str,
    missing_codes: list[str],
    suggested_questions: list[str],
    where_to_go: str | None,
) -> dict:
    validar_opportunity(result, level, access_state)
    return {
        "benefit_id": benefit_id,
        "simple_title": simple_title,
        "result": result,
        "level": level,
        "access_state": access_state,
        "urgency": urgency,
        "benefit": benefit,
        "vulnerability": vulnerability,
        "score": score,
        "position": position,
        "estimated_annual_amount": estimated_annual_amount,
        "benefit_estimated": benefit_estimated,
        "action_type": action_type,
        "why_first": why_first,
        "missing_codes": missing_codes,
        "suggested_questions": suggested_questions,
        "where_to_go": where_to_go,
        "sources": [dict(_SOURCE)],
    }


_OPORTUNIDADES_FAM1: list[dict] = [
    _opp(
        "BEN-001", "Subsidio Familiar", "SI", "CONFIRMADO",
        "ELEGIBLE_SIN_ASIGNACION", 0.1, 0.42, 0.78, 0.56, 1,
        250000.0, False, "FAMILY_ACTION",
        "Califica y nunca lo pidió; vale la pena postular.",
        [], ["¿Tiene el Registro Social de Hogares al día?"],
        "Oficina de ChileAtiende de su comuna.",
    ),
    _opp(
        "BEN-012", "Bono Control Niño Sano", "SI", "PRELIMINAR",
        "PENDIENTE_ANTECEDENTES", 0.1, 0.30, 0.78, 0.33, 2,
        240000.0, True, "ASK_FIRST",
        "Podría corresponder; falta confirmar el control de salud.",
        ["last_health_control_date"],
        ["¿Cuándo fue el último control de salud del niño?"],
        "Centro de salud familiar (CESFAM).",
    ),
    _opp(
        "BEN-018", "Canasta familiar (programa de demostración)", "INDETERMINADO", None,
        "INDETERMINADO", 0.7, 0.0, 0.78, 0.27, 3,
        None, False, "ASK_FIRST",
        "Falta un dato para saber si corresponde.",
        ["housing_type"],
        ["¿Cómo describiría la vivienda del hogar?"],
        None,
    ),
]

_OPORTUNIDADES_FAM2: list[dict] = [
    _opp(
        "BEN-001", "Subsidio Familiar", "SI", "PRELIMINAR",
        "GESTION_RECHAZADA", 0.1, 0.42, 0.40, 0.30, 1,
        250000.0, False, "FOLLOW_UP",
        "Cumple pero la gestión fue rechazada; conviene revisar.",
        [], ["¿Le indicaron el motivo del rechazo?"],
        "Oficina de ChileAtiende de su comuna.",
    ),
]


# --- Familias (listFamiliasByJardin / getFamilia) ----------------------------

FAMILIAS: dict[str, dict] = {
    "FAM-SIM-0001": {
        "summary": {
            "family_id": "FAM-SIM-0001",
            "priority_score": 1.24,
            "vulnerability": 0.78,
            "opportunity_count": 3,
            "conversation_status": "PENDIENTE",
            "traffic_light": "VERDE",
            "top_benefit_ids": ["BEN-001", "BEN-012", "BEN-018"],
        },
        "garden_id": "JARDIN-001",
        "composition": [
            {"role": "ADULT_REFERENCE", "age": 34},
            {"role": "CHILD", "age": 4},
            {"role": "CHILD", "age": 7},
        ],
        "rsh_band": 40,
        "informed": False,
        "benefit_results": [
            {
                "benefit_id": "BEN-001", "result": "SI", "level": "CONFIRMADO",
                "access_state": "ELEGIBLE_SIN_ASIGNACION", "missing_codes": [],
                "trace": [{
                    "rule_id": "RULE-001", "field": "rsh_band",
                    "operator": "LTE", "result": "CUMPLE",
                }],
            },
            {
                "benefit_id": "BEN-012", "result": "SI", "level": "PRELIMINAR",
                "access_state": "PENDIENTE_ANTECEDENTES",
                "missing_codes": ["last_health_control_date"], "trace": [],
            },
            {
                "benefit_id": "BEN-018", "result": "INDETERMINADO", "level": None,
                "access_state": "INDETERMINADO", "missing_codes": ["housing_type"],
                "trace": [],
            },
        ],
        "opportunities": _OPORTUNIDADES_FAM1,
        "context": {
            "family_id": "FAM-SIM-0001",
            "composition": [
                {"role": "ADULT_REFERENCE", "age": 34},
                {"role": "CHILD", "age": 4},
                {"role": "CHILD", "age": 7},
            ],
            "rsh_band": 40,
            "income_band": "UNDER_110K",
            "preferred_format": "TEXT",
            "language": "es",
            "urgency_signals": {
                "recent_emergency": False,
                "limited_quota": None,
                "precarious_housing": False,
            },
            "vulnerability_signals": {
                "rsh_score": 1.0,
                "income_score": 1.0,
                "possible_child_disability": None,
            },
            "inconsistency_codes": [],
            "missing_codes": ["last_health_control_date", "housing_type"],
        },
    },
    "FAM-SIM-0002": {
        "summary": {
            "family_id": "FAM-SIM-0002",
            "priority_score": 0.48,
            "vulnerability": 0.40,
            "opportunity_count": 1,
            "conversation_status": "CONVERSADA",
            "traffic_light": "AMARILLO",
            "top_benefit_ids": ["BEN-001"],
        },
        "garden_id": "JARDIN-002",
        "composition": [
            {"role": "ADULT_REFERENCE", "age": 29},
            {"role": "CHILD", "age": 3},
        ],
        "rsh_band": 70,
        "informed": True,
        "benefit_results": [
            {
                "benefit_id": "BEN-001", "result": "SI", "level": "PRELIMINAR",
                "access_state": "GESTION_RECHAZADA", "missing_codes": [], "trace": [],
            },
        ],
        "opportunities": _OPORTUNIDADES_FAM2,
        "context": {
            "family_id": "FAM-SIM-0002",
            "composition": [
                {"role": "ADULT_REFERENCE", "age": 29},
                {"role": "CHILD", "age": 3},
            ],
            "rsh_band": 70,
            "income_band": "110K_250K",
            "preferred_format": "VISUAL",
            "language": "es",
            "urgency_signals": {
                "recent_emergency": False,
                "limited_quota": False,
                "precarious_housing": None,
            },
            "vulnerability_signals": {
                "rsh_score": 0.6,
                "income_score": 0.75,
                "possible_child_disability": None,
            },
            "inconsistency_codes": [],
            "missing_codes": [],
        },
    },
}

# Valida de una vez las invariantes de benefit_results sintéticos.
for _fam in FAMILIAS.values():
    for _br in _fam["benefit_results"]:
        validar_benefit_result(_br["result"], _br["level"], _br["access_state"])


def familias_de_jardin(garden_id: str) -> list[dict]:
    """FamilySummary de las familias cuyo jardín coincide (coherencia referencial)."""
    return [
        f["summary"] for f in FAMILIAS.values() if f["garden_id"] == garden_id
    ]


def jardin_existe(garden_id: str) -> bool:
    return garden_id in _GARDEN_IDS


def familia_existe(family_id: str) -> bool:
    return family_id in FAMILIAS


# --- KPI (getKpi) ------------------------------------------------------------

def kpi_sintetico(nivel: str, scope_id: str | None, desde: str | None, hasta: str | None) -> dict:
    """KpiResult con nulos y supresión explícitos (API-011)."""
    return {
        "level": nivel,
        "scope_id": scope_id,
        "period_start": desde or "2026-10-01",
        "period_end": hasta or "2026-10-13",
        "total_families": 69,
        "informed_families": 27,
        "informed_percentage": 39.1,
        "total_new_families": 4,
        "informed_new_families": 1,
        "informed_new_percentage": 25.0,
        "opportunity_coverage_percentage": 48.0,
        "suppressed": False,
        "top_gaps": [
            {"benefit_id": "BEN-001", "family_count": 12, "potential_annual_amount": 3000000.0},
            {"benefit_id": "BEN-018", "family_count": 7, "potential_annual_amount": None},
        ],
        "calculated_at": "2026-10-13T12:00:00Z",
        "watermark": "2026-10-13T11:59:00Z",
    }


# --- Borrador de afiche (ingestSyntheticFlyer) -------------------------------

def flyer_draft(synthetic_asset_id: str) -> dict:
    """Borrador sintético que SIEMPRE queda pendiente de revisión humana (API-017)."""
    return {
        "draft_id": "DRAFT-DEMO-0001",
        "synthetic_asset_id": synthetic_asset_id,
        "status": "PENDIENTE_REVISION",
        "confidence": 0.5,
        "name": None,
        "institution": None,
        "requirements": None,
        "commune_id": None,
        "valid_from": None,
        "valid_until": None,
        "public_contact": None,
        "benefit_type": None,
        "warnings": ["REQUIERE_REVISION_HUMANA"],
    }


# --- Preevaluación (createPreevaluacion) -------------------------------------

def preevaluacion_resultado(family_id: str) -> dict:
    """PreevaluationResult SIEMPRE PRELIMINAR, sin mapa EAV ni gate de ingreso."""
    opp = _opp(
        "BEN-001", "Subsidio Familiar", "SI", "PRELIMINAR",
        "PENDIENTE_ANTECEDENTES", 0.1, 0.42, 0.5, 0.37, 1,
        250000.0, False, "ASK_FIRST",
        "Según lo ingresado, podría corresponder; falta acreditar.",
        [], ["¿Tiene el Registro Social de Hogares al día?"],
        "Oficina de ChileAtiende de su comuna.",
    )
    return {
        "family_id": family_id,
        "level": "PRELIMINAR",
        "created_at": "2026-10-13T12:00:00Z",
        "opportunities": [opp],
        "questions": ["¿Tiene el Registro Social de Hogares al día?"],
        "disclaimer": DISCLAIMER,
    }
