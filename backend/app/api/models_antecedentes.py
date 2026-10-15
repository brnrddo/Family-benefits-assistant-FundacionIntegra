"""Modelo del cuerpo de ``POST /familias/{id}/antecedentes`` (propuesta del Rol 3).

Operación PROPUESTA (DEC-039/PREG-039) descrita en
``frontend/docs/PROPUESTA_C3_agregar_informacion.md`` y tipada por el Rol 3 en
``frontend/src/api/proposals/AddFamilyInfoRequestV1.schema.json``. NO forma
parte de C3 v1.0.2: el contrato queda intacto (ver
``backend/app/api/PROPUESTA_ANTECEDENTES.md``).

El cuerpo es un subconjunto CERRADO de ``PreevaluationRequest`` (C3) con
idénticos tipos, enums y límites, más seis preguntas Sí/No (``CAMPOS_MOTOR``,
propuesta fuera de C3, DEC-081) que el motor sabe usar: sin ``garden_id``, ``commune_id``,
``demo_notice_accepted``, nombres, identificadores, contacto ni texto libre
(PRIVACIDAD_DEMO). Semántica de los campos opcionales:

- clave AUSENTE  -> sin cambio (no se declara nada);
- ``null``       -> "No sé" => hecho DESCONOCIDO (nunca ``false`` ni ``0``);
- ``housing_type == "UNKNOWN"`` -> equivalente a ``null``.

Única verificación adicional: ``last_child_health_control_date`` debe ser una
fecha ``YYYY-MM-DD`` válida (``format: date`` del schema del Rol 3). El tipo y
los límites del campo siguen siendo los de ``PreevaluationRequest``.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import Field, field_validator

from app.api.models import _Closed

_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AddFamilyInfoRequestV1(_Closed):
    """``AddFamilyInfoRequestV1``: antecedentes declarados de una familia existente.

    ``data_classification`` es obligatorio (rotulado sintético). El router exige
    además al menos un campo declarado (``minProperties: 2`` del schema del Rol 3).
    """

    data_classification: Literal["SYNTHETIC_DEMO_NOT_A_REAL_PERSON"]
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
    # Preguntas Sí/No de la ficha que alimentan al motor (``CAMPOS_MOTOR``).
    # Propuesta fuera de C3 (DEC-081); ``null`` = "No sé".
    pregnancy_weeks_at_least_threshold: bool | None = None
    has_incompatible_coverage: bool | None = None
    pregnancy_public_network_delivery: bool | None = None
    pregnancy_public_prenatal_control: bool | None = None
    residence_requirement_met: bool | None = None
    age_record_current: bool | None = None

    @field_validator("last_child_health_control_date")
    @classmethod
    def _fecha_iso(cls, valor: str | None) -> str | None:
        """``format: date`` del schema del Rol 3, en el servidor.

        El tipo y los límites son los mismos de ``PreevaluationRequest`` (la
        anotación y el ``metadata`` del campo no cambian); el validador solo
        exige ``YYYY-MM-DD`` válido, porque en esta ruta el valor resuelve un
        ``missing_code`` y baja un nivel. El cliente del Rol 3 ya lo valida.
        """
        if valor is None:
            return None
        if not _FECHA_ISO.match(valor):
            raise ValueError("formato de fecha inválido")
        date.fromisoformat(valor)  # ValueError si la fecha no existe
        return valor


# Campo declarable -> ``missing_code`` de C3. Espeja exactamente (invertido) el
# mapa ``MISSING_CODE_FIELD`` de ``frontend/src/api/proposals/addInfo.ts``; los
# códigos son el enum cerrado de ``FamilyContextView.missing_codes`` (C3).
CAMPO_A_MISSING_CODE: dict[str, str] = {
    "child_age": "child_age",
    "siblings_under_6": "siblings_under_6",
    "siblings_6_14": "siblings_6_14",
    "siblings_15_18": "siblings_15_18",
    "has_rsh": "rsh_status",
    "rsh_band": "rsh_band",
    "household_income_band": "income_band",
    "ssyo_participation": "ssyo_participation",
    "chile_crece_contigo_access": "chile_crece_contigo_access",
    "last_child_health_control_date": "last_health_control_date",
    "child_possible_disability": "possible_disability",
    "child_in_therapy": "therapy",
    "housing_type": "housing_type",
    "household_pregnancy": "pregnancy",
    "household_has_adult_over_65": "adult_over_65",
    "household_formal_employment_or_pension": "employment_or_pension",
    "household_water_payment_difficulty": "water_difficulty",
    "household_food_purchase_difficulty": "food_difficulty",
}

# Los 18 campos de PreevaluationRequest (C3) que la tía puede declarar.
CAMPOS_DECLARABLES = frozenset(CAMPO_A_MISSING_CODE)

# Campos Sí/No de la ficha (propuesta fuera de C3, DEC-081) -> código del motor
# (``datos_faltantes`` de C1). No son ``missing_codes`` de C3; ver
# ``PROPUESTA_ANTECEDENTES.md`` y ``antecedentes_motor.declarados_para_motor``.
CAMPOS_MOTOR: dict[str, str] = {
    "pregnancy_weeks_at_least_threshold": "semanas_gestacion",
    "has_incompatible_coverage": "cobertura_incompatible",
    "pregnancy_public_network_delivery": "parto_red_publica",
    "pregnancy_public_prenatal_control": "control_prenatal_red_publica",
    "residence_requirement_met": "residencia_total_anios",
    "age_record_current": "antecedente_edad_vigente",
}
