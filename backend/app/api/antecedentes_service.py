"""Hechos DECLARADOS y reevaluación de la propuesta ``antecedentes``.

Dos funciones puras:

- ``hechos_declarados``: traduce el cuerpo cerrado a hechos
  ``estado_dato=DECLARADO``, ``acreditada=False`` (nunca acreditados: los
  declara la tía, no una institución).
- ``aplicar_declarados``: reevaluación DETERMINISTA de la ficha sintética.

Límites explícitos (demo con ``E3_MOCK=1``): la elegibilidad la decide el motor
del Rol 1, así que aquí NINGÚN ``result`` cambia, no se promueve
``INDETERMINADO -> SI`` y no se recalculan U/B/V, ``score`` ni ``position``
(esos números vienen de C4). Lo que sí ocurre:

1. un dato declarado con valor conocido resuelve su ``missing_code``;
2. un dato declarado "No sé" conserva (o gana) su ``missing_code`` en el
   beneficio que lo sustenta, en la oportunidad de ese mismo beneficio y en los
   ``missing_codes`` de la vista de contexto (enum cerrado de C3 pensado
   justamente para "no informado"); nunca se degrada a ``false``/``0``;
3. todo resultado u oportunidad sustentado en un hecho declarado baja a
   ``PRELIMINAR`` y nunca queda ``CONFIRMADO``;
4. ``rsh_band`` e ``income_band`` se reflejan tal cual SOLO cuando se declaran
   con valor conocido: son el mismo campo y el mismo enum de C3, no una
   inferencia. Un "No sé" NO borra el valor que vino del motor.
"""
from __future__ import annotations

import copy

from app.api.models import validar_benefit_result, validar_opportunity
from app.api.models_antecedentes import (
    CAMPO_A_MISSING_CODE,
    CAMPOS_MOTOR,
    AddFamilyInfoRequestV1,
)


def hechos_declarados(body: AddFamilyInfoRequestV1) -> list[dict]:
    """Hechos DECLARADO de los campos presentes en el cuerpo.

    Solo mira ``model_fields_set``: una clave AUSENTE no produce hecho (sin
    cambio). ``None`` produce un hecho DESCONOCIDO con ``valor`` ``None``; jamás
    ``False`` ni ``0``. En ``housing_type``, ``"UNKNOWN"`` es "No sé".
    """
    hechos: list[dict] = []
    for campo in sorted(body.model_fields_set - {"data_classification"}):
        valor = getattr(body, campo)
        desconocido = valor is None or (campo == "housing_type" and valor == "UNKNOWN")
        hechos.append(
            {
                "campo": campo,
                "missing_code": CAMPO_A_MISSING_CODE.get(campo) or CAMPOS_MOTOR[campo],
                "valor": valor,
                "desconocido": desconocido,
                "estado_dato": "DECLARADO",
                "acreditada": False,
            }
        )
    return hechos


def _codigos_desconocidos(item: dict, efectivos: dict[str, dict]) -> set[str]:
    """``missing_code`` de los hechos "No sé" que sustentan a ese ítem."""
    return {
        h["missing_code"]
        for h in efectivos.values()
        if h["desconocido"] and _sustentado(item, {h["campo"], h["missing_code"]})
    }


def _sustentado(item: dict, campos: set[str]) -> bool:
    """``True`` si el resultado se apoya en alguno de esos campos/códigos.

    Un resultado se considera sustentado cuando el campo figura entre sus
    ``missing_codes`` o entre los ``field`` de su traza (la traza del motor usa
    el nombre del campo o su ``missing_code``, según la regla).
    """
    referidos = set(item.get("missing_codes", []))
    referidos |= {t["field"] for t in item.get("trace", [])}
    return bool(referidos & campos)


def aplicar_declarados(fam: dict, hechos: list[dict]) -> dict:
    """Ficha reevaluada con los hechos declarados (copia; no muta ``mock_data``).

    Sin hechos devuelve la familia tal cual: comportamiento idéntico al previo.
    """
    if not hechos:
        return fam

    # El último hecho declarado de un campo gana (la tía puede corregirse).
    efectivos: dict[str, dict] = {h["campo"]: h for h in hechos}
    conocidos = {h["missing_code"] for h in efectivos.values() if not h["desconocido"]}
    desconocidos = {h["missing_code"] for h in efectivos.values() if h["desconocido"]}
    # Campo y código: la traza del motor puede nombrar cualquiera de los dos.
    alias = {h["campo"] for h in efectivos.values()} | conocidos | desconocidos

    copia = copy.deepcopy(fam)

    # Los beneficios sustentados en un hecho declarado, con los códigos "No sé"
    # que su ``BenefitResult`` resolvió por traza. La ``Opportunity`` no lleva
    # traza en C3: hereda del ``BenefitResult`` del mismo beneficio tanto el
    # veredicto como esos códigos, para que la misma respuesta no describa el
    # mismo beneficio de dos maneras.
    heredables: dict[str, set[str]] = {
        br["benefit_id"]: _codigos_desconocidos(br, efectivos)
        for br in copia["benefit_results"]
        if _sustentado(br, alias)
    }

    for item in list(copia["benefit_results"]) + list(copia["opportunities"]):
        heredados = heredables.get(item["benefit_id"])
        if heredados is None and not _sustentado(item, alias):
            continue
        codigos = set(item["missing_codes"])
        codigos -= conocidos  # el dato declarado con valor conocido deja de faltar
        # "No sé": el código sigue (o pasa a) faltar donde el motor ya declaró la
        # dependencia (missing_codes previo o traza del beneficio).
        codigos |= _codigos_desconocidos(item, efectivos) | (heredados or set())
        item["missing_codes"] = sorted(codigos)[:20]
        if item["result"] == "SI":
            # Sustentado en un dato declarado y no acreditado: nunca CONFIRMADO.
            item["level"] = "PRELIMINAR"

    # Campos de la ficha y del contexto que son el MISMO campo declarado. Solo
    # con valor CONOCIDO: una declaración de ignorancia no borra un dato de
    # C1/C2 (dejaría la vista de contexto contradictoria con sus propios
    # ``*_score``, que son del motor). El "No sé" se expresa como missing_code.
    if "rsh_band" in efectivos and not efectivos["rsh_band"]["desconocido"]:
        copia["rsh_band"] = efectivos["rsh_band"]["valor"]
        copia["context"]["rsh_band"] = copia["rsh_band"]
    if (
        "household_income_band" in efectivos
        and not efectivos["household_income_band"]["desconocido"]
    ):
        copia["context"]["income_band"] = efectivos["household_income_band"]["valor"]

    # "No informado" a nivel de familia: enum cerrado de FamilyContextView.
    ctx_codes = set(copia["context"]["missing_codes"])
    ctx_codes -= conocidos
    # Solo códigos del enum de C3: los de ``CAMPOS_MOTOR`` son del motor, no de C3.
    ctx_codes |= desconocidos & set(CAMPO_A_MISSING_CODE.values())
    copia["context"]["missing_codes"] = sorted(ctx_codes)[:20]

    # Falla cerrada: ninguna reevaluación puede violar el oneOf de C3.
    for br in copia["benefit_results"]:
        validar_benefit_result(br["result"], br["level"], br["access_state"])
    for op in copia["opportunities"]:
        validar_opportunity(op["result"], op["level"], op["access_state"])

    return copia
