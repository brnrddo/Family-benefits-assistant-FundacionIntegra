"""Carga idempotente del beneficio territorial SOLO DEMO en la SQLite local.

Uso (desde ``backend/``)::

    py -3.11 -m app.demo_territorial.cargar [--db RUTA]
    py -3.11 -m app.db.build_views

Valida el fixture (clasificación, claves cerradas, columnas idénticas a las
tablas del loader, IDs con prefijo demo y sin choques de ``id_parametro``) y,
en una sola transacción, borra las filas demo por ID y las vuelve a insertar.
Los mensajes son fijos: no muestran rutas ni valores.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from app.config import DB_PATH
from app.demo_territorial import FIXTURE_PATH

CLASIFICACION = "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"

# tabla -> (columna ID, prefijo obligatorio)
_TABLAS = {
    "beneficios": ("id_beneficio", "BEN-DEMO-"),
    "beneficios_versiones": ("id_version", "V-DEMO-"),
    "reglas_elegibilidad": ("id_regla", "R-DEMO-"),
    "parametros_version": ("id_parametro", "P-DEMO-"),
}
_CLAVES = frozenset({"data_classification", "leyenda", "tablas"})


class FixtureInvalido(ValueError):
    """El fixture demo no pasa la validación (mensaje fijo)."""


def _leer_fixture(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureInvalido("Fixture demo ilegible") from exc
    if not isinstance(doc, dict) or set(doc) != _CLAVES:
        raise FixtureInvalido("Fixture demo con claves inesperadas")
    if doc["data_classification"] != CLASIFICACION:
        raise FixtureInvalido("Fixture demo sin clasificación sintética")
    if not isinstance(doc["tablas"], dict) or set(doc["tablas"]) != set(_TABLAS):
        raise FixtureInvalido("Fixture demo con tablas inesperadas")
    return doc


def _columnas(conn: sqlite3.Connection, tabla: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{tabla}")')]


def _validar(conn: sqlite3.Connection, tablas: dict) -> None:
    for tabla, (col_id, prefijo) in _TABLAS.items():
        columnas = _columnas(conn, tabla)
        if not columnas:
            raise FixtureInvalido("DB sin las tablas del loader")
        filas = tablas[tabla]
        if not isinstance(filas, list) or not filas:
            raise FixtureInvalido("Fixture demo con una tabla vacía")
        for fila in filas:
            if not isinstance(fila, dict) or set(fila) != set(columnas):
                raise FixtureInvalido("Fixture demo con columnas distintas a la tabla")
            valor = fila[col_id]
            if not isinstance(valor, str) or not valor.startswith(prefijo):
                raise FixtureInvalido("Fixture demo con un ID sin prefijo demo")
    ids_demo = [f["id_parametro"] for f in tablas["parametros_version"]]
    marcas = ",".join("?" for _ in ids_demo)
    choques = conn.execute(
        f"SELECT COUNT(*) FROM parametros_version WHERE id_parametro IN ({marcas}) "
        f"AND id_version NOT IN (SELECT id_version FROM beneficios_versiones "
        f"WHERE id_beneficio LIKE 'BEN-DEMO-%')",
        ids_demo,
    ).fetchone()[0]
    if choques:
        raise FixtureInvalido("Un id_parametro demo choca con otro parámetro")


def cargar(db_path: str | Path, fixture_path: str | Path = FIXTURE_PATH) -> int:
    """Inserta (o reemplaza) las filas demo. Devuelve el número de filas insertadas."""
    doc = _leer_fixture(Path(fixture_path))
    tablas = doc["tablas"]
    conn = sqlite3.connect(Path(db_path))
    try:
        _validar(conn, tablas)
        insertadas = 0
        with conn:  # una transacción: todo o nada
            for tabla, (col_id, _prefijo) in _TABLAS.items():
                columnas = _columnas(conn, tabla)
                ids = [f[col_id] for f in tablas[tabla]]
                marcas = ",".join("?" for _ in ids)
                conn.execute(f'DELETE FROM "{tabla}" WHERE "{col_id}" IN ({marcas})', ids)
                cols = ", ".join(f'"{c}"' for c in columnas)
                valores = ", ".join("?" for _ in columnas)
                conn.executemany(
                    f'INSERT INTO "{tabla}" ({cols}) VALUES ({valores})',
                    [[f[c] for c in columnas] for f in tablas[tabla]],
                )
                insertadas += len(ids)
        return insertadas
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga el beneficio territorial SOLO DEMO en la SQLite local.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Ruta de la SQLite del loader.")
    args = parser.parse_args(argv)
    if not Path(args.db).is_file():
        print("No se encontró la DB del loader. Ejecute primero el loader.")
        return 2
    try:
        n = cargar(args.db)
    except FixtureInvalido as exc:
        print(f"Fixture demo inválido: {exc}")
        return 2
    except sqlite3.Error:
        print("No se pudo escribir la DB del loader.")
        return 2
    print(f"Beneficio SOLO DEMO cargado ({n} filas).")
    print("Ahora ejecute: py -3.11 -m app.db.build_views")
    return 0


if __name__ == "__main__":
    sys.exit(main())
