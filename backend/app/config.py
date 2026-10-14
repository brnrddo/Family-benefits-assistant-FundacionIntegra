"""Configuración central del backend.

Rutas y parámetros compartidos por el loader (M1) y las capas posteriores
(motor de reglas, estado de acceso, etc.). Mantener aquí todo valor que deba
ser configurable para no hardcodearlo en la lógica.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_bool(nombre: str, default: bool) -> bool:
    """Lee una bandera booleana desde entorno (true/1/yes = True)."""
    val = os.environ.get(nombre)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "si", "sí")


# Raíz del backend: .../Aws-breaking-barriers---10-/backend
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Raíz del repositorio: .../Aws-breaking-barriers---10-
REPO_DIR = BACKEND_DIR.parent

# Carpeta con los CSV públicos del dataset E-3.
DATA_PUBLICO_DIR = REPO_DIR / "data" / "publico"

# Base de datos SQLite (efímera, NO versionada; se regenera desde los CSV).
# Permite override por variable de entorno para tests u otros entornos.
DB_PATH = Path(os.environ.get("E3_DB_PATH", str(BACKEND_DIR / "e3.db")))

# Fecha de evaluación (snapshot de la especificación E-3).
# Todas las consultas de vigencia usan esta fecha.
# Vigencia semiabierta: vigente si  vigencia_desde <= FECHA < vigencia_hasta.
FECHA_EVALUACION = os.environ.get("E3_FECHA_EVALUACION", "2026-10-13")

# Corte exclusivo: ninguna versión vigente llega hasta esta fecha (termina antes).
CORTE_EXCLUSIVO = os.environ.get("E3_CORTE_EXCLUSIVO", "2026-10-14")

# --- Supuestos sobre campos ausentes en el dataset (documentados) ------------
# El dataset E-3 no trae ciertos datos que algunas reglas piden. Cuando hay
# EVIDENCIA INDIRECTA de que la condición se cumple, estos supuestos permiten
# resolver el campo como DECLARADO (no acreditado) -> el beneficio puede dar SI
# pero con nivel PRELIMINAR (nunca CONFIRMADO). Son configurables y reversibles.
#
# b) antecedente_edad_vigente: se asume true si el causante es menor de 18
#    (es justo lo que el antecedente por edad certifica). Habilita SUF (BEN-001)
#    y SUF Automático (BEN-002) como PRELIMINAR.
SUPONER_ANTECEDENTE_EDAD = _env_bool("E3_SUPONER_ANTECEDENTE_EDAD", True)

# dias_desde_control: se asume dentro de ventana si el niño tiene un control de
#    salud infantil vigente. Habilita Bono Control Niño Sano (BEN-012) como PRELIMINAR.
SUPONER_CONTROL_VIGENTE = _env_bool("E3_SUPONER_CONTROL_VIGENTE", True)
