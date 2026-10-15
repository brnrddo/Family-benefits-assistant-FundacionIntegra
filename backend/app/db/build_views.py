"""Precálculo persistido + vistas de cruce (M1 · Rol 1).

Materializa las 10.000 evaluaciones (500 familias × 20 beneficios) del motor
(M2) y del estado de acceso (M3) en dos tablas SQLite y crea las vistas de
cruce (`v_familia_beneficio`, `v_oportunidades`, `v_brechas`).

Por qué persistir
------------------
El front (Rol 3) y la API/priorización (Rol 2) necesitan leer resultados con
SQL plano y rápido. En vez de evaluar el motor en cada request, se precalcula
una vez (al construir la imagen/al arrancar) y se consulta la vista.

Uso:
    python -m app.db.build_views          # usa la DB por defecto (e3.db)
    python -m app.db.build_views --db ... # otra ruta

El precálculo de las 500×20 debe correr en < 30 s (requisito del plan Rol 1).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

try:
    from app.access.service import AccesoService
    from app.config import DB_PATH, FECHA_EVALUACION
except ImportError:  # pragma: no cover - permite correr como script suelto
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from app.access.service import AccesoService
    from app.config import DB_PATH, FECHA_EVALUACION

VIEWS_SQL = Path(__file__).resolve().parent / "views.sql"


# --- DDL de las tablas materializadas ---------------------------------------
DDL = """
DROP TABLE IF EXISTS evaluaciones;
CREATE TABLE evaluaciones (
    id_familia        TEXT NOT NULL,
    id_beneficio      TEXT NOT NULL,
    id_version        TEXT,
    fecha_evaluacion  TEXT,
    resultado         TEXT NOT NULL,     -- SI | NO | INDETERMINADO
    nivel             TEXT,              -- CONFIRMADO | PRELIMINAR | NULL
    monto_estimado    INTEGER,
    datos_faltantes   TEXT,              -- JSON array
    motivos           TEXT,              -- JSON array
    entidad_ganadora  TEXT,              -- JSON object
    traza_json        TEXT,              -- JSON array (traza regla-por-regla)
    PRIMARY KEY (id_familia, id_beneficio)
);

DROP TABLE IF EXISTS accesos;
CREATE TABLE accesos (
    id_familia              TEXT NOT NULL,
    id_beneficio            TEXT NOT NULL,
    estado                  TEXT NOT NULL,
    semaforo                TEXT,
    preliminar              INTEGER,     -- 0/1
    tiene_gestion           INTEGER,     -- 0/1
    ultimo_estado_gestion   TEXT,
    id_postulacion          TEXT,
    requiere_accion_familia INTEGER,     -- 0/1
    modalidad_acceso        TEXT,
    canal                   TEXT,
    ventana_desde           TEXT,
    ventana_hasta           TEXT,
    fuente_url              TEXT,
    checklist_json          TEXT,        -- JSON object
    PRIMARY KEY (id_familia, id_beneficio)
);
"""

INDICES = """
CREATE INDEX IF NOT EXISTS idx_eval_familia   ON evaluaciones (id_familia);
CREATE INDEX IF NOT EXISTS idx_eval_beneficio ON evaluaciones (id_beneficio);
CREATE INDEX IF NOT EXISTS idx_eval_resultado ON evaluaciones (resultado);
CREATE INDEX IF NOT EXISTS idx_acc_familia    ON accesos (id_familia);
CREATE INDEX IF NOT EXISTS idx_acc_estado     ON accesos (estado);
"""

# Índices sobre las tablas base del dataset. El motor (M2) y el acceso (M3)
# consultan estas tablas 10.000 veces durante el precálculo; sin índices se
# hacen table scans repetidos. Idempotentes (IF NOT EXISTS).
INDICES_BASE = """
CREATE INDEX IF NOT EXISTS idx_post_fam_ben   ON postulaciones (id_familia, id_beneficio);
CREATE INDEX IF NOT EXISTS idx_postest_post   ON postulaciones_estados (id_postulacion);
CREATE INDEX IF NOT EXISTS idx_cond_integr    ON condiciones_integrante (id_integrante, tipo_condicion);
CREATE INDEX IF NOT EXISTS idx_antec_fam      ON antecedentes_familia (id_familia, tipo_antecedente, subtipo);
CREATE INDEX IF NOT EXISTS idx_rel_origen     ON relaciones_integrantes (id_integrante_origen, tipo_relacion);
CREATE INDEX IF NOT EXISTS idx_rsh_fam        ON rsh_historial (id_familia);
CREATE INDEX IF NOT EXISTS idx_accprev_fam    ON accesos_previos_hogar (id_familia);
CREATE INDEX IF NOT EXISTS idx_benver_ben     ON beneficios_versiones (id_beneficio);
CREATE INDEX IF NOT EXISTS idx_reglas_ver     ON reglas_elegibilidad (id_version);
CREATE INDEX IF NOT EXISTS idx_param_id       ON parametros_version (id_parametro);
"""


def _bool_int(v) -> int:
    return 1 if v else 0


def precalcular(conn: sqlite3.Connection, fecha: str = FECHA_EVALUACION) -> dict[str, int]:
    """Evalúa 500×20, materializa `evaluaciones` + `accesos` y crea las vistas.

    Devuelve un dict con conteos (filas y tiempo en segundos).
    """
    conn.row_factory = sqlite3.Row
    t0 = time.time()

    # 0) índices de aceleración sobre las tablas base que el motor/acceso
    #    consultan 10.000 veces (postulaciones, estados, EAV). Sin estos, el
    #    precálculo hace table scans repetidos y no cumple el objetivo < 30 s.
    conn.executescript(INDICES_BASE)

    # 1) tablas limpias
    conn.executescript(DDL)

    svc = AccesoService(conn, fecha)
    familias = [r[0] for r in conn.execute(
        "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
    beneficios = [r[0] for r in conn.execute(
        "SELECT id_beneficio FROM beneficios ORDER BY id_beneficio").fetchall()]

    filas_eval: list[tuple] = []
    filas_acc: list[tuple] = []

    for fam in familias:
        for ben in beneficios:
            acc = svc.evaluar(fam, ben)
            elig = acc.elegibilidad  # dict (C1)

            filas_eval.append((
                elig["id_familia"], elig["id_beneficio"], elig["id_version"],
                elig["fecha_evaluacion"], elig["resultado"], elig["nivel"],
                elig["monto_estimado"],
                json.dumps(elig["datos_faltantes"], ensure_ascii=False),
                json.dumps(elig["motivos"], ensure_ascii=False),
                json.dumps(elig["entidad_ganadora"], ensure_ascii=False),
                json.dumps(elig["traza"], ensure_ascii=False),
            ))

            chk = acc.checklist
            filas_acc.append((
                acc.id_familia, acc.id_beneficio, acc.estado.value, acc.semaforo,
                _bool_int(acc.preliminar), _bool_int(acc.tiene_gestion),
                acc.ultimo_estado_gestion, acc.id_postulacion,
                _bool_int(chk.requiere_accion_familia) if chk else 0,
                chk.modalidad_acceso if chk else None,
                chk.canal if chk else None,
                chk.ventana_desde if chk else None,
                chk.ventana_hasta if chk else None,
                chk.fuente_url if chk else None,
                json.dumps(chk.to_dict(), ensure_ascii=False) if chk else None,
            ))

    conn.executemany(
        "INSERT INTO evaluaciones VALUES (?,?,?,?,?,?,?,?,?,?,?)", filas_eval)
    conn.executemany(
        "INSERT INTO accesos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", filas_acc)
    conn.executescript(INDICES)

    # 2) vistas de cruce (se inyecta la fecha de evaluación en el SQL).
    sql_vistas = VIEWS_SQL.read_text(encoding="utf-8").replace("__FECHA_EVAL__", fecha)
    conn.executescript(sql_vistas)
    conn.commit()

    segundos = round(time.time() - t0, 2)
    return {
        "evaluaciones": len(filas_eval),
        "accesos": len(filas_acc),
        "familias": len(familias),
        "beneficios": len(beneficios),
        "segundos": segundos,
    }


def construir(db_path: Path | None = None, fecha: str = FECHA_EVALUACION) -> dict[str, int]:
    db_path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(db_path))
    try:
        return precalcular(conn, fecha)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Precálculo persistido (evaluaciones+accesos) y vistas de cruce.")
    parser.add_argument("--db", default=None, help="Ruta de la DB SQLite (default: config).")
    args = parser.parse_args(argv)

    conteos = construir(Path(args.db) if args.db else None)
    print("Precálculo + vistas de cruce")
    print("-" * 44)
    print(f"  familias           {conteos['familias']:>8,}")
    print(f"  beneficios         {conteos['beneficios']:>8,}")
    print(f"  filas evaluaciones {conteos['evaluaciones']:>8,}")
    print(f"  filas accesos      {conteos['accesos']:>8,}")
    print(f"  tiempo (s)         {conteos['segundos']:>8}")
    print("-" * 44)
    objetivo = "OK (< 30 s)" if conteos["segundos"] < 30 else "LENTO (>= 30 s)"
    print(f"  objetivo plan Rol 1: {objetivo}")
    print("  vistas: v_familia_beneficio, v_oportunidades, v_brechas, v_ventanas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
