"""Tests del adaptador YAML del bundle C4 del Rol 4 (``content/``; DEC-022/DEC-048).

``content/`` es de solo lectura: cada caso que manipula el bundle trabaja sobre
una copia en ``tmp_path``. Con ``_rehash`` se recalculan los sha256 y el
``content_bundle_hash`` de la copia para aislar cada validación.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.priority.config import AXIS_SUM_TOLERANCE, ConfigInvalida  # noqa: E402
from app.priority.content_c4 import CONTENT_MANIFEST, cargar_contenido_c4  # noqa: E402

_REPO_DIR = BACKEND_DIR.parent
_CONTENT_DIR = _REPO_DIR / "content"


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture()
def copia(tmp_path: Path) -> Path:
    """Copia relocalizable de ``content/``; devuelve la ruta de su manifest."""
    destino = tmp_path / "content"
    shutil.copytree(_CONTENT_DIR, destino)
    return destino / "manifest.yaml"


def _escribir_yaml(path: Path, doc: dict) -> None:
    texto = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
    path.write_bytes(texto.encode("utf-8"))


def _rehash(manifest_path: Path) -> None:
    """Recalcula sha256 de files[] y content_bundle_hash (SUP-041) en la copia."""
    raiz = manifest_path.parent.parent
    manifest = _yaml(manifest_path)
    for entrada in manifest["files"]:
        entrada["sha256"] = hashlib.sha256((raiz / entrada["path"]).read_bytes()).hexdigest()
    lineas = "".join(
        f"{e['sha256']}  {e['path']}\n"
        for e in sorted(manifest["files"], key=lambda e: e["path"])
    )
    manifest["content_bundle_hash"] = hashlib.sha256(lineas.encode("utf-8")).hexdigest()
    _escribir_yaml(manifest_path, manifest)


# --- bundle real -------------------------------------------------------------


def test_bundle_real_carga_y_expone_ranking():
    contenido = cargar_contenido_c4()
    manifest = _yaml(Path(CONTENT_MANIFEST))
    assert contenido.content_version == manifest["content_version"] == "0.2.1"
    assert contenido.content_bundle_hash == manifest["content_bundle_hash"]
    aw = contenido.ranking.axis_weights
    assert abs(aw["u"] + aw["b"] + aw["v"] - 1.0) <= AXIS_SUM_TOLERANCE
    # Las medianas por jardín salen de content/ (no del default ni del mock).
    for entrada in manifest["ranking"]["benefit_impact"]["garden_income_medians"]:
        assert contenido.ranking.garden_income_median(entrada["garden_id"]) == float(
            entrada["monthly_household_income"]
        )
    assert contenido.ranking.opportunity_score == manifest["ranking"]["opportunity_score"]


def test_bundle_real_catalogo_y_preguntas():
    contenido = cargar_contenido_c4()
    beneficios = _yaml(_CONTENT_DIR / "beneficios.yaml")["beneficios"]
    assert set(contenido.beneficios) == {b["benefit_id"] for b in beneficios}
    for b in beneficios:
        cat = contenido.beneficios[b["benefit_id"]]
        assert cat.simple_title == b["simple_title"]
        assert cat.where_to_go == b["where_to_go"]
        assert cat.official_url == b["official_url"]
    # PREG-045: los tres programas sintéticos no tienen cita HTTPS.
    for bid in ("BEN-018", "BEN-019", "BEN-020"):
        assert contenido.beneficios[bid].official_url is None
    preguntas = {p["missing_code"]: p for p in _yaml(_CONTENT_DIR / "preguntas.yaml")["preguntas"]}
    assert contenido.preguntas["tramo_rsh"] == preguntas["tramo_rsh"]["pregunta"]
    # sin_pregunta + ver resuelve a la pregunta referida.
    assert contenido.preguntas["dias_desde_nacimiento"] == preguntas["parto_red_publica"]["pregunta"]
    # Datos administrativos no generan pregunta a la familia.
    assert "antecedente_edad_vigente" not in contenido.preguntas
    assert "sexo_registral" not in contenido.preguntas


def test_copia_relocalizable_valida(copia: Path):
    assert cargar_contenido_c4(copia).content_version == "0.2.1"


# --- fail-closed -------------------------------------------------------------


def test_manifest_ausente(tmp_path: Path):
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(tmp_path / "content" / "manifest.yaml")


def test_archivo_manipulado_rompe_sha256(copia: Path):
    ruta = copia.parent / "beneficios.yaml"
    ruta.write_bytes(ruta.read_bytes().replace(b"Subsidio Familiar", b"Subsidio Familia", 1))
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_crlf_rompe_sha256(copia: Path):
    ruta = copia.parent / "pesos_priorizacion.yaml"
    ruta.write_bytes(ruta.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_content_bundle_hash_manipulado(copia: Path):
    manifest = _yaml(copia)
    manifest["content_bundle_hash"] = "f" * 64
    _escribir_yaml(copia, manifest)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_falta_clase_obligatoria(copia: Path):
    manifest = _yaml(copia)
    manifest["files"] = [f for f in manifest["files"] if f["kind"] != "I18N"]
    _escribir_yaml(copia, manifest)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_ruta_duplicada(copia: Path):
    manifest = _yaml(copia)
    prompt = next(f for f in manifest["files"] if f["kind"] == "PROMPT")
    manifest["files"].append({"path": prompt["path"], "sha256": prompt["sha256"], "kind": "I18N"})
    _escribir_yaml(copia, manifest)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_suma_ejes_distinta_de_uno(copia: Path):
    pesos_path = copia.parent / "pesos_priorizacion.yaml"
    for path in (copia, pesos_path):
        doc = _yaml(path)
        doc["ranking"]["axis_weights"]["u"] = doc["ranking"]["axis_weights"]["u"] + 0.1
        _escribir_yaml(path, doc)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_ranking_distinto_de_su_archivo_sup040(copia: Path):
    pesos_path = copia.parent / "pesos_priorizacion.yaml"
    doc = _yaml(pesos_path)
    doc["ranking"]["urgency"]["default_score"] = 0.0
    _escribir_yaml(pesos_path, doc)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_url_no_https_en_catalogo(copia: Path):
    ruta = copia.parent / "beneficios.yaml"
    doc = _yaml(ruta)
    doc["beneficios"][0]["official_url"] = "http://ejemplo.invalid/"
    _escribir_yaml(ruta, doc)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)


def test_referencia_ver_rota_en_preguntas(copia: Path):
    ruta = copia.parent / "preguntas.yaml"
    doc = _yaml(ruta)
    for item in doc["preguntas"]:
        if item.get("sin_pregunta") == "SE_RESUELVE_CON_OTRA_PREGUNTA":
            item["ver"] = "codigo_inexistente"
    _escribir_yaml(ruta, doc)
    _rehash(copia)
    with pytest.raises(ConfigInvalida):
        cargar_contenido_c4(copia)
