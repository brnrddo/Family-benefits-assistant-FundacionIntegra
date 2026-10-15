"""Tests del ranking determinista U/B/V (FEAT-001).

Usa fixtures C4 100% sintéticos construidos en el propio test (no dependen de
servicios externos ni del motor). Un caso adicional carga el bundle real del
repo para comprobar que valida contra el schema cerrado.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.access.model import EstadoAcceso  # noqa: E402
from app.engine.model import Nivel, Tri  # noqa: E402
from app.priority.config import (  # noqa: E402
    ConfigInvalida,
    RankingConfig,
    cargar_ranking_config,
)
from app.priority.scoring import (  # noqa: E402
    BenefitInput,
    UrgencySignals,
    VulnerabilitySignals,
    compute_benefit,
    compute_urgency,
    compute_vulnerability,
    family_priority_score,
    score_opportunities,
)

REPO_DIR = BACKEND_DIR.parent


# --- Fixtures sintéticos -----------------------------------------------------

def _ranking_dict() -> dict:
    """Bloque ``ranking`` sintético, con números fáciles de verificar a mano."""
    return {
        "axis_weights": {"u": 0.5, "b": 0.3, "v": 0.2},
        "urgency": {
            "aggregation": "MAX",
            "use_window": False,
            "default_score": 0.1,
            "recent_emergency": {"benefit_id": "BEN-E", "max_age_days": 30, "score": 0.9},
            "newborn_expiry": {"benefit_id": "BEN-N", "window_days": 180, "calculation": "LINEAR_ELAPSED_OVER_WINDOW"},
            "therapy_document_expiry": {"benefit_id": "BEN-T", "window_days": 90, "calculation": "LINEAR_ELAPSED_OVER_WINDOW"},
            "limited_quota": {"score": 0.8},
            "food_insecurity": {"minimum_index": 1, "score": 0.6},
            "precarious_housing": {"housing_types": ["CAMP_OR_OCCUPATION"], "score": 0.7},
            "application_windows": [
                {"maximum_days_remaining": 7, "score": 0.9},
                {"maximum_days_remaining": 30, "score": 0.5},
            ],
        },
        "benefit_impact": {
            "annualization_multipliers": {"MENSUAL": 12, "ANUAL": 1, "UNICA": 1},
            "max_income_share_for_full_score": 0.5,
            "default_monthly_household_income": 500000,
            "garden_income_medians": [
                {"garden_id": "JARDIN-A", "monthly_household_income": 1000000}
            ],
            "service_equivalences": [
                {"benefit_id": "BEN-SVC", "annual_equivalent_amount": 1200000}
            ],
        },
        "vulnerability": {
            "unknown_signals_excluded": True,
            "component_weights": {
                "rsh": 0.3,
                "income": 0.25,
                "health_coverage": 0.15,
                "cse": 0.1,
                "female_head_program": 0.1,
                "possible_child_disability": 0.1,
            },
            "rsh_scores": {
                "band_40": 1.0, "band_50": 0.9, "band_60": 0.75, "band_70": 0.6,
                "band_80": 0.4, "band_90": 0.2, "band_100": 0.1, "no_rsh": 0.5,
            },
            "income_band_scores": {
                "UNDER_110K": 1.0, "110K_250K": 0.75, "250K_400K": 0.4, "OVER_400K": 0.1
            },
            "health_coverage_scores": {"FONASA_A": 0.9, "NO_COVERAGE": 1.0},
            "cse": {"comparison": "LTE", "threshold": 8, "score": 1.0},
            "female_head_program_score": 0.8,
            "possible_child_disability_score": 0.9,
        },
        "opportunity_score": {
            "state_weights": {
                "ELEGIBLE_SIN_ASIGNACION": 1.0,
                "GESTION_RECHAZADA": 0.9,
                "PENDIENTE_ANTECEDENTES": 0.7,
                "INDETERMINADO": 0.5,
                "GESTION_EN_CURSO": 0.3,
                "SIN_CUPO": 0.2,
                "ASIGNADO": 0.0,
            },
            "action_bonus": 0.1,
            "resolvable_question_limit": 5,
        },
        "family_priority": {
            "top_opportunity_count": 3,
            "vulnerability_multiplier": 2.0,
            "not_informed_bonus": 0.15,
            "new_family_bonus": 0.1,
            "new_family_max_age_days": 30,
        },
    }


def _manifest_dict() -> dict:
    """Manifiesto C4 sintético válido contra el schema cerrado."""
    h = "a" * 64
    return {
        "schema_version": "1.0.0",
        "content_version": "0.1.0",
        "content_bundle_hash": "0" * 64,
        "canonical_i18n": "content/i18n/es.json",
        "files": [
            {"path": "content/weights.json", "sha256": h, "kind": "WEIGHTS"},
            {"path": "content/questions.json", "sha256": h, "kind": "QUESTIONS"},
            {"path": "content/benefits.json", "sha256": h, "kind": "BENEFITS"},
            {"path": "content/prompt.json", "sha256": h, "kind": "PROMPT"},
            {"path": "content/accessibility.json", "sha256": h, "kind": "ACCESSIBILITY"},
            {"path": "content/i18n/es.json", "sha256": h, "kind": "I18N"},
        ],
        "ranking": _ranking_dict(),
        "kpi": {"min_cell_size": 5, "max_query_days": 90},
        "accessibility": {
            "canonical_spanish_label_key": "a11y.canonical_es",
            "polly": {
                "enabled": False,
                "evidence_state": "NO_VERIFICADO",
                "smoke_test_evidence_id": None,
                "allowed_voices": [],
                "max_output_characters": 1500,
                "fallback_label_key": "a11y.polly_fallback",
            },
            "translate": {
                "enabled": False,
                "evidence_state": "NO_VERIFICADO",
                "smoke_test_evidence_id": None,
                "source_language": "es",
                "allowed_target_languages": [],
                "max_output_characters": 1500,
                "fallback_label_key": "a11y.translate_fallback",
            },
        },
    }


def _cfg_from(manifest: dict) -> RankingConfig:
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


@pytest.fixture()
def cfg() -> RankingConfig:
    return _cfg_from(_manifest_dict())


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


# --- U: urgencia -------------------------------------------------------------

def test_urgency_sin_senales_usa_default(cfg: RankingConfig):
    assert compute_urgency(UrgencySignals(), cfg) == pytest.approx(0.1)


def test_urgency_es_el_maximo_de_senales_activas(cfg: RankingConfig):
    s = UrgencySignals(limited_quota=True, precarious_housing=True)
    # max(0.8, 0.7) = 0.8
    assert compute_urgency(s, cfg) == pytest.approx(0.8)


def test_urgency_excluye_senales_desconocidas(cfg: RankingConfig):
    # recent_emergency=None no aporta; solo food_insecure activo (0.6).
    s = UrgencySignals(recent_emergency=None, food_insecure=True)
    assert compute_urgency(s, cfg) == pytest.approx(0.6)


def test_urgency_use_window_false_ignora_ventanas(cfg: RankingConfig):
    s = UrgencySignals(application_days_remaining=3)
    # Con use_window=false la ventana no aplica -> default.
    assert compute_urgency(s, cfg) == pytest.approx(0.1)


def test_urgency_use_window_true_aplica_ventana():
    manifest = _manifest_dict()
    manifest["ranking"]["urgency"]["use_window"] = True
    cfg = _cfg_from(manifest)
    s = UrgencySignals(application_days_remaining=3)
    assert compute_urgency(s, cfg) == pytest.approx(0.9)


# --- B: impacto del beneficio -----------------------------------------------

def test_benefit_mensual_desde_c1_con_mediana_de_jardin(cfg: RankingConfig):
    # monto 50.000 mensual -> 600.000 anual; ingreso jardín 1.000.000*12=12.000.000.
    # proporción 0.05; share_full 0.5 -> B = 0.1.
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=50000, periodicidad="MENSUAL",
    )
    b, anual, estimado = compute_benefit(item, cfg, garden_id="JARDIN-A")
    assert anual == pytest.approx(600000)
    assert b == pytest.approx(0.1)
    assert estimado is False


def test_benefit_estimado_por_equivalencia_de_servicio(cfg: RankingConfig):
    # Sin monto; usa service_equivalences (1.200.000 anual) -> benefit_estimated=True.
    item = BenefitInput(
        benefit_id="BEN-SVC", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION,
    )
    b, anual, estimado = compute_benefit(item, cfg, garden_id="JARDIN-A")
    assert anual == pytest.approx(1200000)
    assert estimado is True
    assert b == pytest.approx(0.2)  # 1.2M / 12M = 0.1 ; /0.5 = 0.2


def test_benefit_estimado_cuando_usa_ingreso_default(cfg: RankingConfig):
    # Jardín desconocido -> usa default_monthly_household_income -> estimado=True.
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=50000, periodicidad="MENSUAL",
    )
    _, _, estimado = compute_benefit(item, cfg, garden_id=None)
    assert estimado is True


def test_benefit_satura_en_uno(cfg: RankingConfig):
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=5000000, periodicidad="MENSUAL",
    )
    b, _, _ = compute_benefit(item, cfg, garden_id="JARDIN-A")
    assert b == pytest.approx(1.0)


# --- V: vulnerabilidad -------------------------------------------------------

def test_vulnerability_todos_los_componentes(cfg: RankingConfig):
    s = VulnerabilitySignals(
        rsh_band=40, income_band="UNDER_110K", health_coverage="NO_COVERAGE",
        cse=5, female_head_program=True, possible_child_disability=True,
    )
    # Todos los componentes al máximo relativo -> V alto (no exactamente 1 por mezcla).
    v = compute_vulnerability(s, cfg)
    assert 0.9 <= v <= 1.0


def test_vulnerability_renormaliza_con_componentes_ausentes(cfg: RankingConfig):
    # Solo RSH banda 40 conocido -> V = su score (renormalizado a su único peso).
    s = VulnerabilitySignals(rsh_band=40)
    assert compute_vulnerability(s, cfg) == pytest.approx(1.0)


def test_vulnerability_sin_componentes_es_cero(cfg: RankingConfig):
    assert compute_vulnerability(VulnerabilitySignals(), cfg) == pytest.approx(0.0)


def test_vulnerability_no_rsh_usa_score_dedicado(cfg: RankingConfig):
    s = VulnerabilitySignals(has_rsh=False)
    assert compute_vulnerability(s, cfg) == pytest.approx(0.5)


def test_vulnerability_banda_desconocida_se_excluye(cfg: RankingConfig):
    # rsh_band fuera de las bandas conocidas -> se excluye; income queda solo.
    s = VulnerabilitySignals(rsh_band=999, income_band="110K_250K")
    assert compute_vulnerability(s, cfg) == pytest.approx(0.75)


# --- Puntaje y orden ---------------------------------------------------------

def test_score_pondera_ejes_estado_y_bonus(cfg: RankingConfig):
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=50000, periodicidad="MENSUAL",
        requiere_accion_familia=True,
    )
    ops = score_opportunities(
        [item], UrgencySignals(limited_quota=True),
        VulnerabilitySignals(rsh_band=40), cfg, garden_id="JARDIN-A",
    )
    assert len(ops) == 1
    op = ops[0]
    # U=0.8, B=0.1, V=1.0 ; base = 0.5*0.8 + 0.3*0.1 + 0.2*1.0 = 0.63
    # estado ELEGIBLE_SIN_ASIGNACION peso 1.0 -> 0.63 ; +action_bonus 0.1 = 0.73
    assert op.urgency == pytest.approx(0.8)
    assert op.benefit == pytest.approx(0.1)
    assert op.vulnerability == pytest.approx(1.0)
    assert op.score == pytest.approx(0.73)
    assert op.position == 1


def test_solo_si_e_indeterminado_son_oportunidad(cfg: RankingConfig):
    items = [
        BenefitInput("BEN-NO", Tri.NO, None, EstadoAcceso.NO_APLICA),
        BenefitInput("BEN-IND", Tri.INDETERMINADO, None, EstadoAcceso.INDETERMINADO),
        BenefitInput("BEN-SI", Tri.SI, Nivel.CONFIRMADO, EstadoAcceso.ELEGIBLE_SIN_ASIGNACION),
    ]
    ops = score_opportunities(items, UrgencySignals(), VulnerabilitySignals(), cfg)
    ids = {o.benefit_id for o in ops}
    assert "BEN-NO" not in ids
    assert "BEN-IND" in ids
    assert "BEN-SI" in ids


def test_desempate_por_score_u_b_e_id(cfg: RankingConfig):
    # Dos ítems con mismo score/U pero distinto B, y uno con B igual para romper por id.
    base = dict(result=Tri.SI, level=Nivel.CONFIRMADO,
                access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION)
    items = [
        BenefitInput("BEN-003", monto=50000, periodicidad="MENSUAL", **base),
        BenefitInput("BEN-001", monto=50000, periodicidad="MENSUAL", **base),
        BenefitInput("BEN-002", monto=100000, periodicidad="MENSUAL", **base),
    ]
    ops = score_opportunities(items, UrgencySignals(), VulnerabilitySignals(rsh_band=40),
                              cfg, garden_id="JARDIN-A")
    orden = [o.benefit_id for o in ops]
    # BEN-002 tiene mayor B -> mayor score; BEN-001 y BEN-003 empatan en score/U/B -> id asc.
    assert orden == ["BEN-002", "BEN-001", "BEN-003"]
    assert [o.position for o in ops] == [1, 2, 3]


# --- Prioridad familiar ------------------------------------------------------

def test_prioridad_familiar_suma_top_multiplica_v_y_suma_bonus(cfg: RankingConfig):
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=50000, periodicidad="MENSUAL",
    )
    ops = score_opportunities([item], UrgencySignals(limited_quota=True),
                              VulnerabilitySignals(rsh_band=40), cfg, garden_id="JARDIN-A")
    # score op = 0.5*0.8 + 0.3*0.1 + 0.2*1.0 = 0.63 (sin action_bonus)
    fp = family_priority_score(ops, cfg, conversada=False, family_age_days=10)
    # mult = 1 + (2-1)*1.0 = 2 ; base 0.63*2 = 1.26 ; +0.15 no conversada +0.1 nueva = 1.51
    assert fp.vulnerability == pytest.approx(1.0)
    assert fp.priority_score == pytest.approx(1.51)


def test_prioridad_familiar_sin_bonus_si_conversada_y_antigua(cfg: RankingConfig):
    item = BenefitInput(
        benefit_id="BEN-001", result=Tri.SI, level=Nivel.CONFIRMADO,
        access_state=EstadoAcceso.ELEGIBLE_SIN_ASIGNACION, monto=50000, periodicidad="MENSUAL",
    )
    ops = score_opportunities([item], UrgencySignals(limited_quota=True),
                              VulnerabilitySignals(rsh_band=40), cfg, garden_id="JARDIN-A")
    fp = family_priority_score(ops, cfg, conversada=True, family_age_days=100)
    assert fp.priority_score == pytest.approx(1.26)


# --- Carga y validación de C4 -----------------------------------------------

def test_carga_c4_valido_sintetico(tmp_path: Path):
    path = _write_manifest(tmp_path, _manifest_dict())
    cfg = cargar_ranking_config(path)
    assert cfg.axis_weights["u"] == pytest.approx(0.5)
    assert cfg.content_version == "0.1.0"


def test_carga_bundle_real_del_repo():
    cfg = cargar_ranking_config(REPO_DIR / "content" / "manifest.json")
    aw = cfg.axis_weights
    assert abs(aw["u"] + aw["b"] + aw["v"] - 1.0) < 1e-6


def test_config_invalida_suma_de_ejes_distinta_de_uno(tmp_path: Path):
    manifest = _manifest_dict()
    manifest["ranking"]["axis_weights"] = {"u": 0.5, "b": 0.5, "v": 0.5}
    path = _write_manifest(tmp_path, manifest)
    with pytest.raises(ConfigInvalida):
        cargar_ranking_config(path)


def test_config_invalida_clase_obligatoria_faltante(tmp_path: Path):
    manifest = _manifest_dict()
    # Quitar la clase I18N -> solo 5 clases -> falla el schema cerrado.
    manifest["files"] = [f for f in manifest["files"] if f["kind"] != "I18N"]
    path = _write_manifest(tmp_path, manifest)
    with pytest.raises(ConfigInvalida):
        cargar_ranking_config(path)


def test_config_invalida_default_de_ingreso_ausente(tmp_path: Path):
    manifest = copy.deepcopy(_manifest_dict())
    # Un default no positivo rompe el fallback de mediana (invariante de negocio).
    manifest["ranking"]["benefit_impact"]["default_monthly_household_income"] = 0
    path = _write_manifest(tmp_path, manifest)
    with pytest.raises(ConfigInvalida):
        cargar_ranking_config(path)
