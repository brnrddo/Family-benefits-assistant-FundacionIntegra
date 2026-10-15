"""Modelos Pydantic de los requests públicos C3 (FEAT-003; API-004/API-007).

Reflejan los schemas públicos de C3 campo por campo, con ``extra='forbid'``,
enums exactos y límites de longitud. La respuesta funcional se construye en los
routers desde ``mock_data`` y se valida con jsonschema contra el YAML C3 en los
tests, por lo que aquí sólo se tipan los cuerpos de entrada y las invariantes
``oneOf`` de ``BenefitResult``/``Opportunity`` (expuestas como validadores
reutilizables para los datos sintéticos).

Las invariantes oneOf (API-004):
- ``SI``  -> level ∈ {CONFIRMADO, PRELIMINAR}; access_state de oportunidad.
- ``INDETERMINADO`` -> level null; access_state == INDETERMINADO.
- ``NO|NO_APLICA`` -> level null; access_state == NO_APLICA.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ID_PATTERN = r"^[A-Z0-9][A-Z0-9_-]*$"

# Estados de acceso compatibles con result=SI (coincide con el oneOf de C3).
_ACCESS_SI = {
    "ASIGNADO", "GESTION_EN_CURSO", "GESTION_RECHAZADA",
    "ELEGIBLE_SIN_ASIGNACION", "SIN_CUPO", "PENDIENTE_ANTECEDENTES",
}


class _Closed(BaseModel):
    """Base cerrada: rechaza campos extra (additionalProperties: false)."""

    model_config = ConfigDict(extra="forbid")


# --- Requests públicos -------------------------------------------------------


class FamilyGenerationPublicRequest(_Closed):
    """Cuerpo público de /guion y /mensaje: SOLO benefit_ids (1–3)."""

    benefit_ids: list[str] = Field(min_length=1, max_length=3)

    @field_validator("benefit_ids")
    @classmethod
    def _ids_validos_unicos(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("benefit_ids debe tener elementos únicos")
        import re

        for bid in v:
            if not re.match(_ID_PATTERN, bid) or len(bid) > 80:
                raise ValueError("benefit_id inválido")
        return v


class AssistantPublicRequest(_Closed):
    """Cuerpo público de /asistente: SOLO una pregunta filtrable."""

    question: str = Field(min_length=1, max_length=500)


class ConversationRequest(_Closed):
    """Cuerpo de /familias/{id}/conversaciones (tracking idempotente)."""

    benefit_ids: list[str] = Field(min_length=1, max_length=20)
    next_step: Literal["GO_TO_INSTITUTION", "UPDATE_RSH", "BRING_DOCUMENTS", "NONE"]
    channel: Literal["IN_PERSON", "GROUP_MEETING", "WHATSAPP_PREVIEW", "PRINTED"]
    occurred_at: str
    snapshot_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    origin: Literal["REAL_DEMO", "SIMULADO_DEMO"]

    @field_validator("benefit_ids")
    @classmethod
    def _ids_unicos(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("benefit_ids debe tener elementos únicos")
        import re

        for bid in v:
            if not re.match(_ID_PATTERN, bid) or len(bid) > 80:
                raise ValueError("benefit_id inválido")
        return v


class PreevaluationRequest(_Closed):
    """Cuerpo de /familias/nueva/preevaluacion: ficha sintética cerrada.

    Sin mapa EAV, nombres, identificadores ni texto libre. ``data_classification``
    y ``demo_notice_accepted`` son constantes obligatorias (rotulado sintético).
    """

    data_classification: Literal["SYNTHETIC_DEMO_NOT_A_REAL_PERSON"]
    garden_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    commune_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    demo_notice_accepted: Literal[True]
    child_age: int | None = Field(default=None, ge=0, le=120)
    siblings_under_6: int | None = Field(default=None, ge=0, le=30)
    siblings_6_14: int | None = Field(default=None, ge=0, le=30)
    siblings_15_18: int | None = Field(default=None, ge=0, le=30)
    has_rsh: bool | None = None
    rsh_band: Literal[40, 50, 60, 70, 80, 90, 100] | None = None
    household_income_band: Literal["UNDER_110K", "110K_250K", "250K_400K", "OVER_400K"] | None = None
    ssyo_participation: bool | None = None
    chile_crece_contigo_access: bool | None = None
    last_child_health_control_date: str | None = Field(default=None, max_length=10)
    child_possible_disability: bool | None = None
    child_in_therapy: bool | None = None
    housing_type: Literal[
        "ADEQUATE", "CAMP_OR_OCCUPATION", "ROOM_IN_OTHER_HOME", "OTHER", "UNKNOWN"
    ] | None = None
    household_pregnancy: bool | None = None
    household_has_adult_over_65: bool | None = None
    household_formal_employment_or_pension: bool | None = None
    household_water_payment_difficulty: bool | None = None
    household_food_purchase_difficulty: bool | None = None


# --- Invariantes oneOf (reutilizables por mock_data y tests) -----------------


class InvarianteError(ValueError):
    """Combinación result/level/access_state incoherente con C3 (API-004)."""


def validar_benefit_result(result: str, level: str | None, access_state: str) -> None:
    """Valida el oneOf de ``BenefitResult`` (result admite NO/NO_APLICA)."""
    if result == "SI":
        if level not in ("CONFIRMADO", "PRELIMINAR"):
            raise InvarianteError("SI exige level CONFIRMADO o PRELIMINAR")
        if access_state not in _ACCESS_SI:
            raise InvarianteError("SI exige un access_state de oportunidad")
    elif result == "INDETERMINADO":
        if level is not None or access_state != "INDETERMINADO":
            raise InvarianteError("INDETERMINADO exige level null y access_state INDETERMINADO")
    elif result in ("NO", "NO_APLICA"):
        if level is not None or access_state != "NO_APLICA":
            raise InvarianteError("NO|NO_APLICA exige level null y access_state NO_APLICA")
    else:
        raise InvarianteError(f"result inválido: {result!r}")


def validar_opportunity(result: str, level: str | None, access_state: str) -> None:
    """Valida el oneOf de ``Opportunity`` (solo SI o INDETERMINADO)."""
    if result == "SI":
        if level not in ("CONFIRMADO", "PRELIMINAR"):
            raise InvarianteError("SI exige level CONFIRMADO o PRELIMINAR")
        if access_state not in _ACCESS_SI:
            raise InvarianteError("SI exige un access_state de oportunidad")
    elif result == "INDETERMINADO":
        if level is not None or access_state != "INDETERMINADO":
            raise InvarianteError("INDETERMINADO exige level null y access_state INDETERMINADO")
    else:
        raise InvarianteError(f"Opportunity.result inválido: {result!r}")
