"""Orden de oportunidades por grupo de acción (propuesta DEC-053).

Regla del servidor sobre el enum de estado de acceso, sin números de negocio:
primero lo que la familia puede pedir o le falta completar, después lo que hoy
no tiene cupo y al final lo que ya tiene o ya postuló. Dentro de cada grupo se
conserva el desempate de ``score_opportunities`` (score, U y B descendentes;
``benefit_id`` ascendente).

Funciones puras: no tocan elegibilidad, nivel, acceso ni U/B/V (API-003), solo
reordenan y reasignan ``position``. La prioridad familiar
(``family_priority_score``, C4 §8) NO usa este orden: recibe la lista ordenada
por score tal como sale de ``score_opportunities``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from enum import IntEnum

from app.access.model import EstadoAcceso
from app.priority.scoring import OpportunityScore


class GrupoAccion(IntEnum):
    """Grupos en el orden en que se muestran (el valor solo da el orden)."""

    PUEDE_POSTULAR_O_FALTA_ALGO = 1
    SIN_CUPO = 2
    YA_TIENE_O_YA_POSTULO = 3


GRUPO_POR_ESTADO: dict[EstadoAcceso, GrupoAccion] = {
    EstadoAcceso.ELEGIBLE_SIN_ASIGNACION: GrupoAccion.PUEDE_POSTULAR_O_FALTA_ALGO,
    EstadoAcceso.PENDIENTE_ANTECEDENTES: GrupoAccion.PUEDE_POSTULAR_O_FALTA_ALGO,
    EstadoAcceso.INDETERMINADO: GrupoAccion.PUEDE_POSTULAR_O_FALTA_ALGO,
    EstadoAcceso.SIN_CUPO: GrupoAccion.SIN_CUPO,
    EstadoAcceso.GESTION_EN_CURSO: GrupoAccion.YA_TIENE_O_YA_POSTULO,
    EstadoAcceso.GESTION_RECHAZADA: GrupoAccion.YA_TIENE_O_YA_POSTULO,
    EstadoAcceso.ASIGNADO: GrupoAccion.YA_TIENE_O_YA_POSTULO,
}

# Órdenes de vista de ``listOportunidades`` (C3 ``orden``).
ORDENES = ("prioridad", "urgencia", "beneficio")


def grupo_accion(estado: EstadoAcceso) -> GrupoAccion:
    """Grupo de acción de un estado de oportunidad; ``NO_APLICA`` no tiene."""
    try:
        return GRUPO_POR_ESTADO[EstadoAcceso(estado)]
    except (KeyError, ValueError) as exc:
        raise ValueError("estado de acceso sin grupo de acción") from exc


def ordenar_por_grupo_accion(
    oportunidades: Sequence[OpportunityScore],
) -> list[OpportunityScore]:
    """Orden por grupo y luego por el desempate del ranking; ``position`` 1..n."""
    ordenadas = sorted(
        oportunidades,
        key=lambda o: (
            grupo_accion(o.access_state),
            -o.score,
            -o.urgency,
            -o.benefit,
            o.benefit_id,
        ),
    )
    return [replace(o, position=i) for i, o in enumerate(ordenadas, start=1)]


def ordenar_vista(
    oportunidades: Sequence[OpportunityScore],
    orden: str,
) -> list[OpportunityScore]:
    """Vista de ``orden``: el grupo siempre primero, luego el eje y ``position``.

    ``prioridad`` es el orden de ``position``. ``urgencia`` y ``beneficio``
    ordenan dentro del grupo por U o B descendente. ``position`` no cambia.
    """
    if orden == "prioridad":
        return sorted(oportunidades, key=lambda o: o.position)
    if orden == "urgencia":
        return sorted(
            oportunidades,
            key=lambda o: (grupo_accion(o.access_state), -o.urgency, o.position),
        )
    if orden == "beneficio":
        return sorted(
            oportunidades,
            key=lambda o: (grupo_accion(o.access_state), -o.benefit, o.position),
        )
    raise ValueError("orden de oportunidades desconocido")
