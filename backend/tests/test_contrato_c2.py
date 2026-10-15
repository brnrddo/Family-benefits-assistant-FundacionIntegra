"""El Rol 1 emite el contrato C2 formal (urn:brujula:c2:contexto-familia:v1).

`a_contrato_c2` traduce el `contexto_familia` interno al schema versionado que
consumen Rol 2 y el frontend. Estos tests verifican:
  - invariantes del contrato sin dependencias (claves requeridas, enums,
    data_classification, vocabulario cerrado, roles, bandas);
  - validación COMPLETA contra el JSON Schema si `jsonschema` está instalado
    (si no, esa parte se omite, no falla);
  - que ningún dato prohibido (nombres, RUT, id de integrante) se cuele.
  - 500 familias producen C2 con forma válida.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.context import a_contrato_c2, construir_contexto

REPO_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = (REPO_DIR / ".kiro" / "specs" / "_shared" / "contracts"
               / "C2-contexto-familia.schema.json")

FAM = "FAM-SIM-E3-00100"

CAMPOS_VALIDOS = {
    "composition", "child.age", "siblings.under_6", "siblings.6_14",
    "siblings.15_18", "rsh.has_registry", "rsh.band", "income.per_capita_band",
    "ssyo.participation", "chile_crece_contigo.access",
    "child.last_health_control_date", "child.possible_disability",
    "child.in_therapy", "housing.type", "household.pregnancy",
    "household.has_adult_over_65", "household.formal_employment_or_pension",
    "household.water_payment_difficulty", "household.food_purchase_difficulty",
}
ROLES_VALIDOS = {"ADULTA_REFERENCIA", "NINO_JARDIN", "OTRO_ADULTO"}
INGRESO_VALIDO = {"UNDER_110K", "110K_250K", "250K_400K", "OVER_400K", None}
ESTADO_VALIDO = {"OBSERVADO", "DECLARADO", "DESCONOCIDO", "NO_APLICA"}


@pytest.fixture()
def fecha():
    from app.config import FECHA_EVALUACION
    return FECHA_EVALUACION


@pytest.fixture()
def c2(conn, fecha):
    ctx = construir_contexto(FAM, conn=conn, fecha=fecha)
    return a_contrato_c2(ctx)


def test_claves_requeridas(c2):
    requeridas = {
        "data_classification", "id_familia", "fuente", "hechos", "procedencia",
        "inconsistencias", "no_informado", "senales_urgencia",
        "senales_vulnerabilidad", "formato_preferido", "idioma_mensaje",
    }
    assert requeridas == set(c2.keys())


def test_data_classification_y_fuente(c2):
    assert c2["data_classification"] == "SYNTHETIC_DEMO_NOT_A_REAL_PERSON"
    assert c2["fuente"] in ("FICHA_SINTETICA", "FICHA_DIGITAL")


def test_hechos_vocabulario_cerrado(c2):
    for h in c2["hechos"]:
        assert set(h.keys()) == {"campo", "valor", "estado_dato", "acreditada"}
        assert h["campo"] in CAMPOS_VALIDOS, f"campo fuera del contrato: {h['campo']}"
        assert h["estado_dato"] in ESTADO_VALIDO
        assert isinstance(h["acreditada"], bool)


def test_composition_roles_y_edades(c2):
    comp = next(h for h in c2["hechos"] if h["campo"] == "composition")
    assert comp["valor"] is None or isinstance(comp["valor"], list)
    for m in comp["valor"] or []:
        assert set(m.keys()) == {"rol", "edad"}
        assert m["rol"] in ROLES_VALIDOS
        assert isinstance(m["edad"], int) and 0 <= m["edad"] <= 120


def test_rsh_band_e_ingreso_enums(c2):
    band = next(h for h in c2["hechos"] if h["campo"] == "rsh.band")
    assert band["valor"] in (40, 50, 60, 70, 80, 90, 100, None)
    income = next(h for h in c2["hechos"] if h["campo"] == "income.per_capita_band")
    assert income["valor"] in INGRESO_VALIDO


def test_procedencia_coherente_con_hechos(c2):
    campos_hechos = {h["campo"] for h in c2["hechos"]}
    campos_proc = {p["campo"] for p in c2["procedencia"]}
    assert campos_proc <= CAMPOS_VALIDOS
    # Cada hecho tiene su procedencia.
    assert campos_hechos == campos_proc


def test_sin_datos_prohibidos(c2):
    """Serializado, el C2 no contiene identificadores ni ids de integrante."""
    blob = json.dumps(c2, ensure_ascii=False).lower()
    for prohibido in ("per-sim", "rut", "nombre", "apellido", "telefono"):
        assert prohibido not in blob, f"posible fuga: {prohibido}"


def test_validacion_jsonschema_si_disponible(c2):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=c2, schema=schema)


def test_quinientas_familias_validas(conn, fecha):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validador = jsonschema.Draft202012Validator(schema)
    familias = [r[0] for r in conn.execute(
        "SELECT id_familia FROM familias ORDER BY id_familia").fetchall()]
    assert len(familias) == 500
    for fam in familias:
        ctx = construir_contexto(fam, conn=conn, fecha=fecha)
        c2 = a_contrato_c2(ctx)
        errores = sorted(validador.iter_errors(c2), key=lambda e: e.path)
        assert not errores, f"{fam}: {[e.message for e in errores][:3]}"
