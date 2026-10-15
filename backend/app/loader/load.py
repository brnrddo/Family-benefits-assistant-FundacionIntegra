"""Loader del dataset E-3 (M1).

Carga los 23 CSV públicos de `data/publico/` en una base SQLite, una tabla por
archivo. Enfoque "SQL directo":

- Todas las columnas se cargan como TEXT. Las fechas ISO (``2026-10-13``) se
  comparan correctamente como texto, lo que evita sorpresas de parsing. Donde
  una consulta necesite tratar un valor como número usa ``CAST`` puntual.
- Los valores vacíos del CSV se cargan como ``NULL`` (no como cadena vacía).
- Lectura explícita en UTF-8 (en Windows el default puede no serlo).

Uso:
    python -m app.loader.load            # crea la DB si no existe
    python -m app.loader.load --force    # reconstruye la DB desde cero

El JSON consolidado (`dataset_e3.json`) NO se carga a una tabla: queda
disponible como archivo para el frontend si se necesita más adelante.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

try:
    # Ejecución como módulo:  python -m app.loader.load
    from app.config import DATA_PUBLICO_DIR, DB_PATH, FECHA_EVALUACION
except ImportError:  # pragma: no cover - fallback si se corre como script suelto
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from app.config import DATA_PUBLICO_DIR, DB_PATH, FECHA_EVALUACION

# Índices mínimos para las consultas de humo y las capas siguientes.
# (tabla, columna) -> se crea un índice simple.
INDICES = [
    ("integrantes", "id_familia"),
    ("beneficios_versiones", "id_beneficio"),
    ("reglas_elegibilidad", "id_version"),
]


def _descubrir_csv(data_dir: Path) -> list[Path]:
    """Lista los CSV de la carpeta de datos, en orden estable."""
    if not data_dir.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de datos: {data_dir}")
    return sorted(data_dir.glob("*.csv"))


def _nombre_tabla(csv_path: Path) -> str:
    """Nombre de tabla = nombre de archivo sin extensión."""
    return csv_path.stem


def _crear_tabla_desde_csv(conn: sqlite3.Connection, csv_path: Path) -> int:
    """Crea una tabla a partir de un CSV y la puebla. Devuelve nº de filas."""
    tabla = _nombre_tabla(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        lector = csv.reader(fh)
        try:
            encabezados = next(lector)
        except StopIteration:
            raise ValueError(f"CSV vacío (sin encabezados): {csv_path}")

        # Nombres de columna entre comillas dobles para tolerar cualquier
        # carácter. Todas TEXT (enfoque SQL directo + CAST en consulta).
        cols_ddl = ", ".join(f'"{c}" TEXT' for c in encabezados)
        conn.execute(f'DROP TABLE IF EXISTS "{tabla}"')
        conn.execute(f'CREATE TABLE "{tabla}" ({cols_ddl})')

        placeholders = ", ".join("?" for _ in encabezados)
        insert_sql = f'INSERT INTO "{tabla}" VALUES ({placeholders})'
        ncols = len(encabezados)

        filas = 0
        lote: list[list[str | None]] = []
        for raw in lector:
            # Normaliza longitud por si alguna fila viene corta/larga.
            if len(raw) < ncols:
                raw = raw + [""] * (ncols - len(raw))
            elif len(raw) > ncols:
                raw = raw[:ncols]
            # Vacío -> NULL
            fila = [valor if valor != "" else None for valor in raw]
            lote.append(fila)
            if len(lote) >= 1000:
                conn.executemany(insert_sql, lote)
                filas += len(lote)
                lote.clear()
        if lote:
            conn.executemany(insert_sql, lote)
            filas += len(lote)

    return filas


def _crear_indices(conn: sqlite3.Connection) -> None:
    """Crea índices mínimos si las tablas/columnas existen."""
    for tabla, columna in INDICES:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (tabla,),
        ).fetchone()
        if not existe:
            continue
        idx = f"idx_{tabla}_{columna}"
        conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{tabla}" ("{columna}")')


def construir_db(
    data_dir: Path | None = None,
    db_path: Path | None = None,
    force: bool = False,
) -> dict[str, int]:
    """(Re)construye la base SQLite desde los CSV públicos.

    Devuelve un dict ``{tabla: nº_filas}``.

    - Si la DB existe y ``force`` es False, no recarga (devuelve conteos leídos
      de la DB existente).
    - Con ``force=True`` reconstruye el archivo desde cero.
    """
    data_dir = Path(data_dir) if data_dir else DATA_PUBLICO_DIR
    db_path = Path(db_path) if db_path else DB_PATH

    if db_path.exists() and not force:
        return contar_filas(db_path)

    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    csvs = _descubrir_csv(data_dir)
    conteos: dict[str, int] = {}

    conn = sqlite3.connect(db_path)
    try:
        for csv_path in csvs:
            filas = _crear_tabla_desde_csv(conn, csv_path)
            conteos[_nombre_tabla(csv_path)] = filas
        _crear_indices(conn)
        conn.commit()
    finally:
        conn.close()

    return conteos


def _listar_tablas(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def contar_filas(db_path: Path | None = None) -> dict[str, int]:
    """Devuelve ``{tabla: nº_filas}`` para todas las tablas de la DB."""
    db_path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        conteos: dict[str, int] = {}
        for tabla in _listar_tablas(conn):
            n = conn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
            conteos[tabla] = n
        return conteos
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga el dataset E-3 (CSV públicos) a SQLite."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconstruye la DB desde cero aunque ya exista.",
    )
    args = parser.parse_args(argv)

    conteos = construir_db(force=args.force)

    total = sum(conteos.values())
    print(f"Base de datos: {DB_PATH}")
    print(f"Fecha de evaluación: {FECHA_EVALUACION}")
    print(f"Tablas cargadas: {len(conteos)}")
    print("-" * 48)
    for tabla in sorted(conteos):
        print(f"  {tabla:<28} {conteos[tabla]:>8,}")
    print("-" * 48)
    print(f"  {'TOTAL filas':<28} {total:>8,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
