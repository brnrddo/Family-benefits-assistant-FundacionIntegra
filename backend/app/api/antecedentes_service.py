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
2. un dato declarado "No sé" conserva su ``missing_code`` donde ya figuraba y
   lo agrega a los ``missing_codes`` de la vista de contexto (enum cerrado de
   C3 pensado justamente para "no informado"); nunca se degrada a ``false``/``0``;
3. todo resultado u oportunidad sustentado en un hecho declarado baja a
   ``PRELIMINAR`` y nunca queda ``CONFIRMADO``;
4. ``rsh_band`` e ``income_band`` se reflejan tal cual cuando se declaran: son
   el mismo campo y el mismo enum de C3, no una inferencia.
"""
from __future__ import annotations

import copy

from app.api.models import validar_benefit_result, validar_opportunity
from app.api.models_antecedentes import (
    CAMPO_A_MISSING_CODE,
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
                "missing_code": CAMPO_A_MISSING_CODE[campo],
                "valor": valor,
                "desconocido": desconocido,
                "estado_dato": "DECLARADO",
                "acreditada": False,
            }
        )
    return hechos


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

    # Los beneficios sustentados en un hecho declarado. La oportunidad no lleva
    # traza en C3: hereda el veredicto de su ``BenefitResult`` (mismo beneficio).
    tocados = {
        br["benefit_id"] for br in copia["benefit_results"] if _sustentado(br, alias)
    }

    for item in list(copia["benefit_results"]) + list(copia["opportunities"]):
        if not (_sustentado(item, alias) or item["benefit_id"] in tocados):
            continue
        codigos = set(item["missing_codes"])
        codigos -= conocidos  # el dato declarado con valor conocido deja de faltar
        # "No sé": el código sigue (o pasa a) faltar, pero solo donde el propio
        # motor ya declaró la dependencia (missing_codes previo o traza).
        codigos |= {
            h["missing_code"]
            for h in efectivos.values()
            if h["desconocido"] and _sustentado(item, {h["campo"], h["missing_code"]})
        }
        item["missing_codes"] = sorted(codigos)[:20]
        if item["result"] == "SI":
            # Sustentado en un dato declarado y no acreditado: nunca CONFIRMADO.
            item["level"] = "PRELIMINAR"

    # Campos de la ficha y del contexto que son el MISMO campo declarado.
    if "rsh_band" in efectivos:
        h = efectivos["rsh_band"]
        copia["rsh_band"] = None if h["desconocido"] else h["valor"]
        copia["context"]["rsh_band"] = copia["rsh_band"]
    if "household_income_band" in efectivos:
        h = efectivos["household_income_band"]
        copia["context"]["income_band"] = None if h["desconocido"] else h["valor"]

    # "No informado" a nivel de familia: enum cerrado de FamilyContextView.
    ctx_codes = set(copia["context"]["missing_codes"])
    ctx_codes -= conocidos
    ctx_codes |= desconocidos
    copia["context"]["missing_codes"] = sorted(ctx_codes)[:20]

    # Falla cerrada: ninguna reevaluación puede violar el oneOf de C3.
    for br in copia["benefit_results"]:
        validar_benefit_result(br["result"], br["level"], br["access_state"])
    for op in copia["opportunities"]:
        validar_opportunity(op["result"], op["level"], op["access_state"])

    return copia
