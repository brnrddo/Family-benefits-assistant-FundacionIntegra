"""Configuración central del backend.

Rutas y parámetros compartidos por el loader (M1) y las capas posteriores
(motor de reglas, estado de acceso, etc.). Mantener aquí todo valor que deba
ser configurable para no hardcodearlo en la lógica.
"""
from __future__ import annotations

import os
from pathlib import Path

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
