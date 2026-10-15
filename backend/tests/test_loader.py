"""Tests de verificación del loader M1 (CSV E-3 -> SQLite)."""
from __future__ import annotations

from app.config import FECHA_EVALUACION

# Conteos esperados por tabla (verificados contra el dataset E-3).
CONTEOS_ESPERADOS = {
    "accesos_previos_causantes": 125,
    "accesos_previos_hogar": 125,
    "antecedentes_familia": 5500,
    "beneficios": 20,
    "beneficios_fuentes": 40,
    "beneficios_versiones": 41,
    "comunas": 20,
    "condiciones_integrante": 4700,
    "familias": 500,
    "fuentes": 22,
    "integrantes": 1700,
    "jardines": 50,
    "pagos_beneficios": 2343,
    "parametros_fuentes": 158,
    "parametros_version": 158,
    "postulaciones": 2383,
    "postulaciones_causantes": 1782,
    "postulaciones_estados": 6702,
    "reglas_elegibilidad": 151,
    "reglas_fuentes": 278,
    "relaciones_integrantes": 1000,
    "rsh_historial": 500,
    "versiones_fuentes": 287,
}


def _tablas(conn) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def test_se_crean_23_tablas(conn):
    tablas = _tablas(conn)
    assert len(tablas) == 23, f"Se esperaban 23 tablas, hay {len(tablas)}: {sorted(tablas)}"
    assert tablas == set(CONTEOS_ESPERADOS), "Nombres de tabla no coinciden con lo esperado"


def test_conteos_de_filas(conn):
    for tabla, esperado in CONTEOS_ESPERADOS.items():
        n = conn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        assert n == esperado, f"{tabla}: esperado {esperado}, obtenido {n}"


def test_familia_1_con_integrantes_y_encoding(conn):
    """Humo A: join familias<->integrantes y encoding UTF-8 correcto."""
    integrantes = conn.execute(
        """
        SELECT i.id_integrante, i.parentesco
        FROM familias f
        JOIN integrantes i ON i.id_familia = f.id_familia
        WHERE f.id_familia = ?
        """,
        ("FAM-SIM-E3-00001",),
    ).fetchall()
    assert len(integrantes) >= 1, "La familia 1 debe tener al menos un integrante"

    # Encoding: 'Automático' en beneficios.csv debe conservar la tilde.
    nombre = conn.execute(
        "SELECT nombre FROM beneficios WHERE id_beneficio = ?", ("BEN-002",)
    ).fetchone()[0]
    assert "á" in nombre, f"Encoding UTF-8 incorrecto en beneficios.nombre: {nombre!r}"
    assert nombre == "Subsidio Familiar Automático"


def test_version_vigente_ben001(conn):
    """Humo B: versión vigente de BEN-001 a la fecha de evaluación = V002 (única)."""
    filas = conn.execute(
        """
        SELECT id_version
        FROM beneficios_versiones
        WHERE id_beneficio = ?
          AND vigencia_desde <= ?
          AND (vigencia_hasta IS NULL OR ? < vigencia_hasta)
        """,
        ("BEN-001", FECHA_EVALUACION, FECHA_EVALUACION),
    ).fetchall()
    assert len(filas) == 1, f"Debe haber exactamente 1 versión vigente, hay {len(filas)}"
    assert filas[0][0] == "V002"


def test_ben016_tiene_3_versiones(conn):
    """Humo C: BEN-016 tiene 3 versiones; una muestra del resto tiene 2."""
    n16 = conn.execute(
        "SELECT COUNT(*) FROM beneficios_versiones WHERE id_beneficio = ?",
        ("BEN-016",),
    ).fetchone()[0]
    assert n16 == 3, f"BEN-016 debe tener 3 versiones, tiene {n16}"

    n01 = conn.execute(
        "SELECT COUNT(*) FROM beneficios_versiones WHERE id_beneficio = ?",
        ("BEN-001",),
    ).fetchone()[0]
    assert n01 == 2, f"BEN-001 debe tener 2 versiones, tiene {n01}"


def test_valor_vacio_queda_como_null(conn):
    """Un valor vacío del CSV debe cargarse como NULL (no cadena vacía)."""
    # integrantes.vigencia_hasta suele venir vacío (vigencia abierta).
    nulos = conn.execute(
        "SELECT COUNT(*) FROM integrantes WHERE vigencia_hasta IS NULL"
    ).fetchone()[0]
    assert nulos > 0, "Se esperaban NULLs en integrantes.vigencia_hasta"

    # Y no debe haber cadenas vacías representando ese nulo.
    vacias = conn.execute(
        "SELECT COUNT(*) FROM integrantes WHERE vigencia_hasta = ''"
    ).fetchone()[0]
    assert vacias == 0, "No deben existir cadenas vacías; los vacíos van como NULL"


def test_idempotencia_sin_force(conn, db_path):
    """Reconstruir sin force no cambia los conteos (no recarga)."""
    from app.loader.load import construir_db

    antes = conn.execute("SELECT COUNT(*) FROM familias").fetchone()[0]
    construir_db(db_path=db_path, force=False)  # no debe tocar nada
    despues = conn.execute("SELECT COUNT(*) FROM familias").fetchone()[0]
    assert antes == despues == 500


# --- resiliencia / falla cerrada ante CSV corrupto --------------------------

def test_csv_vacio_sin_encabezados_falla(tmp_path):
    """Un CSV totalmente vacío (sin encabezados) debe fallar explícito, no cargar."""
    import pytest

    from app.loader.load import _crear_tabla_desde_csv
    import sqlite3

    vacio = tmp_path / "tabla_vacia.csv"
    vacio.write_text("", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    try:
        with pytest.raises(ValueError):
            _crear_tabla_desde_csv(conn, vacio)
    finally:
        conn.close()


def test_filas_corta_y_larga_se_normalizan(tmp_path):
    """Fila con menos columnas -> se rellena con NULL; con más -> se trunca.

    El loader no debe caerse ni descartar la fila: debe normalizar su longitud
    al número de encabezados (comportamiento documentado en load.py).
    """
    import sqlite3

    from app.loader.load import _crear_tabla_desde_csv

    csv_path = tmp_path / "demo.csv"
    csv_path.write_text(
        "a,b,c\n"
        "1,2,3\n"       # exacta
        "4,5\n"          # corta -> c debe quedar NULL
        "6,7,8,9\n",     # larga -> se trunca a 3
        encoding="utf-8",
    )
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        filas = _crear_tabla_desde_csv(conn, csv_path)
        assert filas == 3
        rows = conn.execute('SELECT a, b, c FROM "demo" ORDER BY a').fetchall()
        assert rows[1]["a"] == "4" and rows[1]["b"] == "5" and rows[1]["c"] is None
        larga = conn.execute('SELECT a, b, c FROM "demo" WHERE a = ?', ("6",)).fetchone()
        assert larga["b"] == "7" and larga["c"] == "8"  # el 9 se descartó
    finally:
        conn.close()
