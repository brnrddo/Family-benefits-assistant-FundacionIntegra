"""ESBOZO — Arma `infrastructure/cdk/build/lambda/` para empaquetar las Lambdas.

El `precompute_stack.py` hace `lambda_.Code.from_asset("build/lambda")`. Este
script prepara esa carpeta: copia el código del backend (`backend/app`), los
handlers de `infrastructure/lambdas/` y la base `e3.db` de solo-lectura.

Uso:
    # 1) generar la base y el precálculo (igual que en local)
    cd backend
    python -m app.loader.load --force
    python -m app.db.build_views
    # 2) armar el bundle de la Lambda
    cd ../infrastructure
    python build_lambda.py

Resultado:
    infrastructure/cdk/build/lambda/
        app/                      ← backend/app (motor M2/M3, stdlib)
        prepare_manifest.py
        snapshot_partition_builder.py
        calcular_cupo.py
        cupo_ben018.py
        validar_snapshot.py
        e3.db                     ← base solo-lectura (se monta en /opt o raíz)

Nota: `e3.db` NO se versiona (está en .gitignore). Se regenera siempre desde los
CSV antes del build, para que la nube reproduzca lo mismo que local.
"""
from __future__ import annotations

import os
import shutil
import stat
import time
from pathlib import Path

INFRA_DIR = Path(__file__).resolve().parent
REPO_DIR = INFRA_DIR.parent
BACKEND_APP = REPO_DIR / "backend" / "app"
E3_DB = REPO_DIR / "backend" / "e3.db"
HANDLERS = INFRA_DIR / "lambdas"
BUILD_DIR = INFRA_DIR / "cdk" / "build" / "lambda"

HANDLER_FILES = [
    "prepare_manifest.py",
    "snapshot_partition_builder.py",
    "calcular_cupo.py",
    "cupo_ben018.py",
    "validar_snapshot.py",
]


def _ignore_pycache(_dir, names):
    return [n for n in names if n in ("__pycache__",) or n.endswith(".pyc")]


def _on_rm_error(func, path, _exc):
    """Reintento para Windows/OneDrive: quita solo-lectura y reintenta."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        time.sleep(0.2)
        try:
            func(path)
        except Exception:
            pass  # el rmtree final tolera restos; se sobrescriben


def _limpiar(build_dir: Path) -> None:
    if not build_dir.exists():
        return
    # onexc (3.12+) con fallback a onerror para versiones previas.
    try:
        shutil.rmtree(build_dir, onexc=_on_rm_error)
    except TypeError:  # pragma: no cover - Python < 3.12
        shutil.rmtree(build_dir, onerror=lambda f, p, e: _on_rm_error(f, p, e))


def main() -> int:
    if not BACKEND_APP.is_dir():
        print(f"ERROR: no existe {BACKEND_APP}")
        return 1
    if not E3_DB.is_file():
        print(f"ERROR: no existe {E3_DB}. Corre primero el loader + build_views "
              "(ver docstring).")
        return 1

    # Limpiar y recrear el bundle.
    _limpiar(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # 1) backend/app
    shutil.copytree(BACKEND_APP, BUILD_DIR / "app", ignore=_ignore_pycache)

    # 2) handlers
    for h in HANDLER_FILES:
        shutil.copy2(HANDLERS / h, BUILD_DIR / h)

    # 3) base de datos de solo-lectura
    shutil.copy2(E3_DB, BUILD_DIR / "e3.db")

    total = sum(1 for _ in BUILD_DIR.rglob("*") if _.is_file())
    print(f"OK: bundle en {BUILD_DIR} ({total} archivos)")
    print("    E3_DB_PATH en la Lambda debe apuntar a la e3.db incluida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
