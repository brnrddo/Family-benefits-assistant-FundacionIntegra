"""Beneficio territorial SOLO DEMO (B2, propuesta DEC-071).

``BEN-DEMO-LOCAL-01`` es inventado: no existe y no viene en los datos del
Rol 1. Se agrega a la SQLite local con ``python -m app.demo_territorial.cargar``
para mostrar un apoyo que solo aplica a quienes viven en una comuna. El motor
del Rol 1 lo evalúa sin cambios; este paquete no decide elegibilidad.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEMO_BENEFIT_ID = "BEN-DEMO-LOCAL-01"

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures" / "demo_territorial" / "beneficio_local_demo.json"
)


def demo_cargado(db_path: str | Path) -> bool:
    """True si la DB trae el beneficio demo. False ante cualquier error o ausencia."""
    path = Path(db_path)
    if not path.is_file():
        return False
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            fila = conn.execute(
                "SELECT 1 FROM beneficios WHERE id_beneficio = ?", (DEMO_BENEFIT_ID,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return fila is not None
