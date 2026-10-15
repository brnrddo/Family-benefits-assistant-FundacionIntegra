"""Priorización determinista U/B/V (Rol 2, FEAT-001).

Carga y valida el bundle C4 (``config``) y calcula el ranking de oportunidades
y la prioridad familiar (``scoring``) sin ningún número de negocio hardcodeado.
El texto generado nunca participa: la decisión es determinista (API-003).
"""
from __future__ import annotations

from app.priority.config import (
    ConfigInvalida,
    RankingConfig,
    cargar_ranking_config,
)
from app.priority.scoring import (
    BenefitInput,
    FamilyPriority,
    OpportunityScore,
    UrgencySignals,
    VulnerabilitySignals,
    compute_benefit,
    compute_urgency,
    compute_vulnerability,
    family_priority_score,
    score_opportunities,
)

__all__ = [
    "ConfigInvalida",
    "RankingConfig",
    "cargar_ranking_config",
    "BenefitInput",
    "FamilyPriority",
    "OpportunityScore",
    "UrgencySignals",
    "VulnerabilitySignals",
    "compute_benefit",
    "compute_urgency",
    "compute_vulnerability",
    "family_priority_score",
    "score_opportunities",
]
