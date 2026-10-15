"""Ranking determinista U/B/V (FEAT-001; API-002/API-003).

Funciones puras: dado el resultado de elegibilidad (C1), el estado de acceso,
las señales de contexto autorizadas (C2) y un ``RankingConfig`` cargado del
bundle C4, calculan U (urgencia), B (impacto del beneficio) y V (vulnerabilidad)
en ``[0,1]``, el puntaje de oportunidad y la prioridad familiar.

Reglas de oro:
- NINGÚN número de negocio está hardcodeado aquí; todo proviene de ``RankingConfig``.
- El texto generado NUNCA entra: estas funciones no llaman IA ni alteran C1.
- Señales desconocidas/no derivables se excluyen (no bajan ni suben el score).
- Solo resultados ``SI`` o ``INDETERMINADO`` llegan a ser oportunidades.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.access.model import EstadoAcceso
from app.engine.model import Nivel, Tri
from app.priority.config import RankingConfig

# Estados de acceso que pueden ser oportunidad (coinciden con el oneOf de C3).
_ESTADOS_OPORTUNIDAD = {
    EstadoAcceso.ASIGNADO,
    EstadoAcceso.GESTION_EN_CURSO,
    EstadoAcceso.GESTION_RECHAZADA,
    EstadoAcceso.ELEGIBLE_SIN_ASIGNACION,
    EstadoAcceso.SIN_CUPO,
    EstadoAcceso.PENDIENTE_ANTECEDENTES,
    EstadoAcceso.INDETERMINADO,
}


@dataclass(frozen=True)
class UrgencySignals:
    """Señales de urgencia autorizadas (C2). ``None`` = desconocida -> se excluye.

    Cada bandera corresponde a una señal del bloque ``urgency`` de C4. Con
    ``use_window=false`` (Demo inicial) las ventanas por edad no se evalúan.
    """

    recent_emergency: bool | None = None
    limited_quota: bool | None = None
    precarious_housing: bool | None = None
    food_insecure: bool | None = None
    application_days_remaining: int | None = None


@dataclass(frozen=True)
class VulnerabilitySignals:
    """Componentes de vulnerabilidad autorizados (C2). ``None`` = desconocido.

    Un componente ``None`` se excluye del denominador (renormalización por los
    pesos presentes), según ``unknown_signals_excluded`` del bundle C4.
    """

    rsh_band: int | None = None          # 40..100
    has_rsh: bool | None = None
    income_band: str | None = None       # UNDER_110K | 110K_250K | 250K_400K | OVER_400K
    health_coverage: str | None = None   # FONASA_A | NO_COVERAGE
    cse: int | None = None               # 0..34
    female_head_program: bool | None = None
    possible_child_disability: bool | None = None


@dataclass(frozen=True)
class BenefitInput:
    """Entrada por beneficio para el scoring (derivada de C1 + acceso)."""

    benefit_id: str
    result: Tri
    level: Nivel | None
    access_state: EstadoAcceso
    # Monto declarado por el motor (si existe) y su periodicidad para anualizar.
    monto: float | None = None
    periodicidad: str | None = None       # MENSUAL | ANUAL | UNICA
    requiere_accion_familia: bool = False
    resolvable_question_count: int = 0


@dataclass(frozen=True)
class OpportunityScore:
    """Resultado del ranking para un beneficio (alineado con C3 Opportunity).

    No incluye los campos de presentación (``simple_title``, ``why_first``,
    ``sources``, etc.): esos los compone la capa API (FEAT-003) a partir de C4.
    """

    benefit_id: str
    result: Tri
    level: Nivel | None
    access_state: EstadoAcceso
    urgency: float
    benefit: float
    vulnerability: float
    score: float
    position: int
    estimated_annual_amount: float | None
    benefit_estimated: bool


def _clamp01(valor: float) -> float:
    return max(0.0, min(1.0, valor))


# --- U: urgencia -------------------------------------------------------------

def compute_urgency(
    signals: UrgencySignals,
    cfg: RankingConfig,
) -> float:
    """U = MAX de las señales activas; ``default_score`` si no hay ninguna.

    Con ``use_window=false`` las señales por ventana de edad (recién nacido,
    documento de terapia) no se evalúan. Las señales desconocidas (``None``) se
    excluyen por completo.
    """
    u = cfg.urgency
    candidatos: list[float] = []

    if signals.recent_emergency is True:
        candidatos.append(float(u["recent_emergency"]["score"]))
    if signals.limited_quota is True:
        candidatos.append(float(u["limited_quota"]["score"]))
    if signals.precarious_housing is True:
        candidatos.append(float(u["precarious_housing"]["score"]))
    if signals.food_insecure is True:
        candidatos.append(float(u["food_insecurity"]["score"]))

    if u.get("use_window") and signals.application_days_remaining is not None:
        # Ventanas de postulación ordenadas: primera cuyo umbral cubre los días.
        ventanas = sorted(
            u["application_windows"], key=lambda w: w["maximum_days_remaining"]
        )
        for ventana in ventanas:
            if signals.application_days_remaining <= ventana["maximum_days_remaining"]:
                candidatos.append(float(ventana["score"]))
                break

    if not candidatos:
        return _clamp01(float(u["default_score"]))
    return _clamp01(max(candidatos))


# --- B: impacto del beneficio -----------------------------------------------

def compute_benefit(
    item: BenefitInput,
    cfg: RankingConfig,
    garden_id: str | None,
) -> tuple[float, float | None, bool]:
    """B = monto anualizado / (ingreso anual del hogar) saturando en el divisor.

    Devuelve ``(B, monto_anual_estimado, benefit_estimated)``.

    - El monto puede venir del motor (C1) con su periodicidad, o de una
      equivalencia de servicio de C4 (``service_equivalences``), caso en que
      ``benefit_estimated=True``.
    - El ingreso del hogar usa la mediana por jardín o el default de C4.
    - ``max_income_share_for_full_score`` satura la proporción: alcanzar esa
      fracción del ingreso anual ya otorga B=1.
    """
    bi = cfg.benefit_impact
    multipliers = bi["annualization_multipliers"]

    monto_anual: float | None = None
    estimado = False

    if item.monto is not None and item.periodicidad in multipliers:
        monto_anual = float(item.monto) * float(multipliers[item.periodicidad])
    else:
        equivalencia = cfg.service_equivalence(item.benefit_id)
        if equivalencia is not None:
            monto_anual = equivalencia
            estimado = True

    if monto_anual is None or monto_anual <= 0:
        return 0.0, monto_anual, estimado

    ingreso_mensual = cfg.garden_income_median(garden_id)
    if garden_id is None or not any(
        e["garden_id"] == garden_id for e in bi["garden_income_medians"]
    ):
        # Se usó el default de ingreso -> el componente B queda estimado.
        estimado = True

    ingreso_anual = ingreso_mensual * float(multipliers["MENSUAL"])
    proporcion = monto_anual / ingreso_anual
    share_full = float(bi["max_income_share_for_full_score"])
    b = _clamp01(proporcion / share_full)
    return b, monto_anual, estimado


# --- V: vulnerabilidad -------------------------------------------------------

def compute_vulnerability(
    signals: VulnerabilitySignals,
    cfg: RankingConfig,
) -> float:
    """V = suma ponderada de componentes conocidos, renormalizada por sus pesos.

    Los componentes desconocidos (``None``) se excluyen del numerador y del
    denominador (``unknown_signals_excluded``). Si no hay ningún componente
    conocido, V=0.
    """
    v = cfg.vulnerability
    pesos = v["component_weights"]

    aportes: list[tuple[float, float]] = []  # (peso, score_componente)

    # RSH: banda conocida o explícitamente "sin RSH".
    rsh_score = _rsh_component(signals, v)
    if rsh_score is not None:
        aportes.append((float(pesos["rsh"]), rsh_score))

    if signals.income_band is not None:
        band_scores = v["income_band_scores"]
        if signals.income_band in band_scores:
            aportes.append((float(pesos["income"]), float(band_scores[signals.income_band])))

    if signals.health_coverage is not None:
        hc = v["health_coverage_scores"]
        if signals.health_coverage in hc:
            aportes.append(
                (float(pesos["health_coverage"]), float(hc[signals.health_coverage]))
            )

    if signals.cse is not None:
        aportes.append((float(pesos["cse"]), _cse_component(signals.cse, v)))

    if signals.female_head_program is not None:
        score = float(v["female_head_program_score"]) if signals.female_head_program else 0.0
        aportes.append((float(pesos["female_head_program"]), score))

    if signals.possible_child_disability is not None:
        score = (
            float(v["possible_child_disability_score"])
            if signals.possible_child_disability
            else 0.0
        )
        aportes.append((float(pesos["possible_child_disability"]), score))

    peso_total = sum(p for p, _ in aportes)
    if peso_total <= 0:
        return 0.0
    ponderado = sum(p * s for p, s in aportes)
    return _clamp01(ponderado / peso_total)


def _rsh_component(signals: VulnerabilitySignals, v: dict) -> float | None:
    scores = v["rsh_scores"]
    if signals.rsh_band is not None:
        clave = f"band_{signals.rsh_band}"
        if clave in scores:
            return float(scores[clave])
        return None
    if signals.has_rsh is False:
        return float(scores["no_rsh"])
    return None


def _cse_component(cse: int, v: dict) -> float:
    regla = v["cse"]
    umbral = int(regla["threshold"])
    cumple = cse <= umbral if regla["comparison"] == "LTE" else cse >= umbral
    return float(regla["score"]) if cumple else 0.0


# --- Puntaje de oportunidad y prioridad familiar -----------------------------

def opportunity_raw_score(
    u: float,
    b: float,
    v: float,
    access_state: EstadoAcceso,
    requiere_accion_familia: bool,
    cfg: RankingConfig,
) -> float:
    """Combina U/B/V con los pesos de eje, el peso de estado y el bonus de acción."""
    aw = cfg.axis_weights
    base = aw["u"] * u + aw["b"] * b + aw["v"] * v
    os_cfg = cfg.opportunity_score
    peso_estado = float(os_cfg["state_weights"][access_state.value])
    score = base * peso_estado
    if requiere_accion_familia:
        score += float(os_cfg["action_bonus"])
    return score


def score_opportunities(
    items: list[BenefitInput],
    urgency_signals: UrgencySignals,
    vulnerability_signals: VulnerabilitySignals,
    cfg: RankingConfig,
    garden_id: str | None = None,
) -> list[OpportunityScore]:
    """Puntúa y ordena las oportunidades de una familia.

    Solo entran los ítems con ``result`` ``SI`` o ``INDETERMINADO`` y un estado
    de acceso de oportunidad. Orden/desempate: ``score`` desc, U desc, B desc,
    ``benefit_id`` asc. La vulnerabilidad V es de la familia (igual para todos
    sus beneficios); U depende de las señales; B es por beneficio.
    """
    u = compute_urgency(urgency_signals, cfg)
    v = compute_vulnerability(vulnerability_signals, cfg)

    parciales: list[OpportunityScore] = []
    for item in items:
        if item.result not in (Tri.SI, Tri.INDETERMINADO):
            continue
        if item.access_state not in _ESTADOS_OPORTUNIDAD:
            continue
        b, monto_anual, estimado = compute_benefit(item, cfg, garden_id)
        score = opportunity_raw_score(
            u, b, v, item.access_state, item.requiere_accion_familia, cfg
        )
        parciales.append(
            OpportunityScore(
                benefit_id=item.benefit_id,
                result=item.result,
                level=item.level,
                access_state=item.access_state,
                urgency=u,
                benefit=b,
                vulnerability=v,
                score=score,
                position=0,  # se asigna tras ordenar
                estimated_annual_amount=monto_anual,
                benefit_estimated=estimado,
            )
        )

    parciales.sort(
        key=lambda o: (-o.score, -o.urgency, -o.benefit, o.benefit_id)
    )

    ordenadas: list[OpportunityScore] = []
    for idx, op in enumerate(parciales, start=1):
        ordenadas.append(
            OpportunityScore(
                benefit_id=op.benefit_id,
                result=op.result,
                level=op.level,
                access_state=op.access_state,
                urgency=op.urgency,
                benefit=op.benefit,
                vulnerability=op.vulnerability,
                score=op.score,
                position=idx,
                estimated_annual_amount=op.estimated_annual_amount,
                benefit_estimated=op.benefit_estimated,
            )
        )
    return ordenadas


@dataclass(frozen=True)
class FamilyPriority:
    """Prioridad agregada de una familia para la cola de la tía."""

    priority_score: float
    vulnerability: float
    top_opportunity_count: int


def family_priority_score(
    opportunities: list[OpportunityScore],
    cfg: RankingConfig,
    *,
    conversada: bool,
    family_age_days: int | None = None,
) -> FamilyPriority:
    """Prioridad familiar: suma de los top-N scores de oportunidad + bonus.

    - Toma los primeros ``top_opportunity_count`` por score (ya vienen ordenados).
    - Multiplica por ``vulnerability_multiplier`` ponderado por la V de la familia.
    - Suma ``not_informed_bonus`` si la familia no ha sido conversada.
    - Suma ``new_family_bonus`` si ``family_age_days < new_family_max_age_days``.
    """
    fp = cfg.family_priority
    top_n = int(fp["top_opportunity_count"])
    top = opportunities[:top_n]

    base = sum(o.score for o in top)
    v_familia = opportunities[0].vulnerability if opportunities else 0.0
    multiplicador = 1.0 + (float(fp["vulnerability_multiplier"]) - 1.0) * v_familia
    score = base * multiplicador

    if not conversada:
        score += float(fp["not_informed_bonus"])
    if family_age_days is not None and family_age_days < int(fp["new_family_max_age_days"]):
        score += float(fp["new_family_bonus"])

    return FamilyPriority(
        priority_score=score,
        vulnerability=v_familia,
        top_opportunity_count=len(top),
    )
