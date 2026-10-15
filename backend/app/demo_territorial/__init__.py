"""Beneficios territoriales SOLO DEMO (B2, propuesta DEC-071).

``BEN-DEMO-LOCAL-01`` (comunal) y ``BEN-DEMO-REGIONAL-01`` (regional) son
inventados: no existen ni vienen en los datos del Rol 1. Se agregan a la SQLite
local con ``python -m app.demo_territorial.cargar`` para mostrar apoyos que solo
aplican por comuna o por región. El motor del Rol 1 los evalúa sin cambios; este
paquete no decide elegibilidad.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEMO_BENEFIT_ID = "BEN-DEMO-LOCAL-01"
DEMO_BENEFIT_ID_REGIONAL = "BEN-DEMO-REGIONAL-01"

# Todos los IDs demo territoriales (comunal + regional). El overlay de
# presentación C4 y el texto de catálogo cubren a todos.
DEMO_BENEFIT_IDS = (DEMO_BENEFIT_ID, DEMO_BENEFIT_ID_REGIONAL)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures" / "demo_territorial" / "beneficio_local_demo.json"
)


def demo_cargado(db_path: str | Path) -> bool:
    """True si la DB trae algún beneficio demo. False ante error o ausencia."""
    path = Path(db_path)
    if not path.is_file():
        return False
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            marcas = ",".join("?" for _ in DEMO_BENEFIT_IDS)
            fila = conn.execute(
                f"SELECT 1 FROM beneficios WHERE id_beneficio IN ({marcas})",
                DEMO_BENEFIT_IDS,
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return fila is not None
