"""Serializadores de las respuestas funcionales de C3 compartidos por routers.

Existe para que una misma forma de respuesta no se construya dos veces: la
ficha ``FamilyDetail`` la devuelven ``GET /familias/{id}`` y la propuesta
``POST /familias/{id}/antecedentes``, y deben ser idénticas byte a byte en su
estructura (C3 ``FamiliaDetailEnvelope``, sin cambios).
"""
from __future__ import annotations

import copy

from app.api.deps import DISCLAIMER


def familia_detail_data(fam: dict) -> dict:
    """``FamilyDetail`` de C3 (8 claves exactas) desde la familia sintética.

    Devuelve copias profundas: ningún consumidor puede mutar ``mock_data``.
    """
    return {
        "family_id": fam["summary"]["family_id"],
        "garden_id": fam["garden_id"],
        "composition": copy.deepcopy(fam["composition"]),
        "rsh_band": fam["rsh_band"],
        "informed": fam["informed"],
        "top_opportunities": copy.deepcopy(fam["opportunities"][:3]),
        "benefit_results": copy.deepcopy(fam["benefit_results"]),
        "disclaimer": DISCLAIMER,
    }
