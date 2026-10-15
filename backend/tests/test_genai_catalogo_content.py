"""Tests del loader del catálogo C4 de ``content/`` (Rol 4; DEC-055, DEC-058).

- ``content/`` real carga: 20 beneficios en orden, hashes del manifest, nombres
  i18n, citas HTTPS solo donde existen (BEN-018/019/020 sin cita, PREG-045) y
  versiones de los prompts.
- Solo lectura: los bytes de ``content/`` no cambian al cargar.
- CRLF tolerado (DEC-045: el sha256 es sobre bytes LF).
- Cada manipulación de una copia falla cerrada con su código fijo.
- La política de copy marca promesas y no marca las frases del Rol 4.

Las copias se hacen en ``tmp_path``; ``content/`` del repo nunca se modifica.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.genai import content_catalog  # noqa: E402
from app.genai.content_catalog import (  # noqa: E402
    ContenidoInvalido,
    cargar_catalogo_contenido,
)
from app.genai.template_provider import (  # noqa: E402
    PH_INSTITUCION,
    PH_TITULOS,
    contiene_promesa,
)

REPO_DIR = BACKEND_DIR.parent
CONTENT_DIR = REPO_DIR / "content"
IDS = [f"BEN-{n:03d}" for n in range(1, 21)]
SIN_CITA = {"BEN-018", "BEN-019", "BEN-020"}


def _beneficios_yaml() -> dict:
    with (CONTENT_DIR / "beneficios.yaml").open(encoding="utf-8") as fh:
        return {b["benefit_id"]: b for b in yaml.safe_load(fh)["beneficios"]}


def _i18n() -> dict:
    with (CONTENT_DIR / "i18n" / "es.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def _sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _copiar(tmp_path: Path) -> Path:
    """Copia ``content/`` a ``tmp_path/content`` y devuelve la ruta del manifest."""
    shutil.copytree(CONTENT_DIR, tmp_path / "content")
    return tmp_path / "content" / "manifest.yaml"


def _resellar(root: Path) -> None:
    """Recalcula sha256 y ``content_bundle_hash`` (SUP-041) de la copia."""
    manifest_path = root / "content" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for f in manifest["files"]:
        f["sha256"] = _sha_lf(root / f["path"])
    lineas = "".join(
        f"{f['sha256']}  {f['path']}\n"
        for f in sorted(manifest["files"], key=lambda f: f["path"])
    )
    manifest["content_bundle_hash"] = hashlib.sha256(lineas.encode("utf-8")).hexdigest()
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _reemplazar(path: Path, viejo: str, nuevo: str) -> None:
    texto = path.read_text(encoding="utf-8")
    assert viejo in texto, "la manipulación no encontró su texto"
    path.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8", newline="\n")


# --- content/ real ---------------------------------------------------------------


def test_content_real_carga_completo():
    cat = cargar_catalogo_contenido()
    manifest = yaml.safe_load((CONTENT_DIR / "manifest.yaml").read_text(encoding="utf-8"))
    beneficios = _beneficios_yaml()
    i18n = _i18n()

    assert cat.content_version == "0.2.1"
    assert cat.content_bundle_hash == manifest["content_bundle_hash"]
    assert list(cat.entradas) == IDS
    for bid, e in cat.entradas.items():
        b = beneficios[bid]
        assert e.title == i18n[f"benefit.{bid.lower()}.name"] == b["simple_title"]
        assert e.description == b["description"]
        assert e.institution == b["institution"]
        assert e.where_to_go == b["where_to_go"]
        if bid in SIN_CITA:
            assert (e.source_id, e.source_url) == ("", "")
        else:
            assert (e.source_id, e.source_url) == (b["official_source_id"], b["official_url"])
            assert e.source_url.startswith("https://")
    assert cat.entradas["BEN-001"].source_id == "F004"
    for pid in ("PROMPT-GUION", "PROMPT-MENSAJE-FAMILIA", "PROMPT-ASISTENTE-CATALOGO"):
        assert cat.prompt_versions[pid] == "1.0.0"


def test_plantillas_son_las_del_rol4():
    """Las frases marco son literales de ``## Plantilla de respaldo`` (DEC-054)."""
    p = cargar_catalogo_contenido().plantillas
    guion = (CONTENT_DIR / "prompts" / "guion.md").read_text(encoding="utf-8")
    mensaje = (CONTENT_DIR / "prompts" / "mensaje_familia.md").read_text(encoding="utf-8")
    asistente = (CONTENT_DIR / "prompts" / "asistente_catalogo.md").read_text(encoding="utf-8")
    aviso = " Orientación referencial; no determina derechos. Confirmar en la institución."

    assert f"> script: {p.guion}{aviso}" in guion
    assert f"> whatsapp_preview: {p.whatsapp}{aviso}" in mensaje
    assert f"> printable_card.title: {p.tarjeta_titulo}\n" in mensaje
    assert f"> printable_card.introduction: {p.tarjeta_introduccion}\n" in mensaje
    assert f"> printable_card.sections[].reason: {p.seccion_razon}\n" in mensaje
    assert f"> printable_card.sections[].action: {p.seccion_accion}\n" in mensaje
    assert f"> answer: {p.asistente_individual}{aviso}" in asistente
    assert f"> answer: {p.asistente_catalogo}{aviso}" in asistente
    assert PH_TITULOS in p.guion and PH_TITULOS in p.whatsapp and PH_TITULOS in p.asistente_catalogo
    assert PH_INSTITUCION in p.seccion_accion
    assert p.etiqueta_donde_ir == _i18n()["card_v1.where_label"]


def test_carga_es_solo_lectura():
    antes = {p: p.read_bytes() for p in CONTENT_DIR.rglob("*") if p.is_file()}
    cargar_catalogo_contenido()
    despues = {p: p.read_bytes() for p in CONTENT_DIR.rglob("*") if p.is_file()}
    assert antes == despues


def test_crlf_tolerado(tmp_path):
    manifest = _copiar(tmp_path)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    for f in data["files"]:
        path = tmp_path / f["path"]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    manifest.write_bytes(manifest.read_bytes().replace(b"\n", b"\r\n"))
    cat = cargar_catalogo_contenido(manifest)
    assert list(cat.entradas) == IDS


def test_default_manifest_se_lee_al_llamar(tmp_path, monkeypatch):
    manifest = _copiar(tmp_path)
    (tmp_path / "content" / "beneficios.yaml").write_bytes(b"x")
    monkeypatch.setattr(content_catalog, "DEFAULT_MANIFEST", manifest)
    with pytest.raises(ContenidoInvalido) as exc:
        cargar_catalogo_contenido()
    assert exc.value.codigo == "C4_SHA256_DISTINTO"


# --- manipulaciones (falla cerrada con código fijo) ------------------------------


def _byte_de_mas(root: Path) -> None:
    path = root / "content" / "beneficios.yaml"
    path.write_bytes(path.read_bytes() + b" ")


def _bundle_hash_falso(root: Path) -> None:
    manifest = root / "content" / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    _reemplazar(manifest, data["content_bundle_hash"], "f" * 64)


def _clave_extra_manifest(root: Path) -> None:
    manifest = root / "content" / "manifest.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "extra: 1\n", encoding="utf-8")


def _archivo_ausente(root: Path) -> None:
    _reemplazar(root / "content" / "manifest.yaml",
                "path: content/preguntas.yaml", "path: content/no_existe.yaml")


def _manifest_ilegible(root: Path) -> None:
    (root / "content" / "manifest.yaml").write_text("files: [\n  - {path: ", encoding="utf-8")


def _ruta_repetida(root: Path) -> None:
    manifest = root / "content" / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    original = next(f for f in data["files"] if f["kind"] == "QUESTIONS")
    data["files"].append(dict(original, kind="SYNTHETIC_ASSET_MANIFEST"))
    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _sin_prompt_guion(root: Path) -> None:
    manifest = root / "content" / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["files"] = [f for f in data["files"] if f["path"] != "content/prompts/guion.md"]
    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _resellar(root)


def _descripcion_con_promesa(root: Path) -> None:
    _reemplazar(root / "content" / "beneficios.yaml",
                "Ayuda con los gastos de crianza.",
                "Ayuda con los gastos de crianza. Usted tiene derecho a este apoyo.")
    _resellar(root)


def _url_http(root: Path) -> None:
    _reemplazar(root / "content" / "beneficios.yaml",
                "official_url: https://", "official_url: http://")
    _resellar(root)


def _clave_extra_beneficio(root: Path) -> None:
    _reemplazar(root / "content" / "beneficios.yaml",
                "    source_ids: [F004, F900]\n", "    source_ids: [F004, F900]\n    extra: x\n")
    _resellar(root)


def _i18n_editado(root: Path, clave: str, valor: str) -> None:
    path = root / "content" / "i18n" / "es.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[clave] = valor
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _resellar(root)


def _aviso_alterado(root: Path) -> None:
    _i18n_editado(root, "notice.referential", "Orientación referencial.")


def _nombre_distinto(root: Path) -> None:
    _i18n_editado(root, "benefit.ben-005.name", "Subsidio del agua")


def _placeholder_ajeno(root: Path) -> None:
    _reemplazar(root / "content" / "prompts" / "guion.md",
                "{{catalog_items[].title}}. Vale la pena",
                "{{catalog_items[].title}} {{context.composition}}. Vale la pena")
    _resellar(root)


def _script_sin_aviso(root: Path) -> None:
    _reemplazar(root / "content" / "prompts" / "guion.md",
                "cada apoyo. Orientación referencial; no determina derechos. Confirmar en la institución.",
                "cada apoyo.")
    _resellar(root)


@pytest.mark.parametrize(
    ("manipular", "codigo"),
    [
        (_byte_de_mas, "C4_SHA256_DISTINTO"),
        (_bundle_hash_falso, "C4_BUNDLE_HASH_DISTINTO"),
        (_clave_extra_manifest, "C4_SCHEMA_INVALIDO"),
        (_archivo_ausente, "C4_ARCHIVO_AUSENTE"),
        (_manifest_ilegible, "C4_MANIFEST_ILEGIBLE"),
        (_ruta_repetida, "C4_RUTA_INVALIDA"),
        (_sin_prompt_guion, "C4_CLASE_FALTANTE"),
        (_descripcion_con_promesa, "C4_BENEFITS_INVALIDO"),
        (_url_http, "C4_BENEFITS_INVALIDO"),
        (_clave_extra_beneficio, "C4_BENEFITS_INVALIDO"),
        (_aviso_alterado, "C4_I18N_INVALIDO"),
        (_nombre_distinto, "C4_I18N_INVALIDO"),
        (_placeholder_ajeno, "C4_PROMPT_INVALIDO"),
        (_script_sin_aviso, "C4_PROMPT_INVALIDO"),
    ],
    ids=lambda v: v.__name__ if callable(v) else v,
)
def test_manipulacion_falla_cerrada(tmp_path, manipular, codigo):
    manifest = _copiar(tmp_path)
    manipular(tmp_path)
    with pytest.raises(ContenidoInvalido) as exc:
        cargar_catalogo_contenido(manifest)
    assert exc.value.codigo == codigo
    # El mensaje es solo el código: sin rutas ni valores.
    assert str(exc.value) == codigo


def test_resellar_sin_cambios_sigue_cargando(tmp_path):
    """Control positivo del helper: resellar una copia intacta no la invalida."""
    manifest = _copiar(tmp_path)
    _resellar(tmp_path)
    assert list(cargar_catalogo_contenido(manifest).entradas) == IDS


# --- política de copy (DEC-054) --------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "Usted tiene derecho a este apoyo.",
        "Ustedes tienen derecho a este apoyo.",
        "Su familia recibirá el aporte.",
        "Le corresponde este bono.",
        "Les corresponden estos apoyos.",
        "Según su ficha, podría corresponderle.",
        "El pago está garantizado.",
        "Tiene el apoyo asegurado.",
        "Su familia califica.",
        "Usted es elegible.",
        "Recibe $ cada mes.",
        "Son 25000 al mes.",
        "Son 25.000 al mes.",
    ],
)
def test_contiene_promesa_detecta(texto):
    assert contiene_promesa(texto)


def test_contiene_promesa_no_marca_frases_del_rol4():
    p = cargar_catalogo_contenido().plantillas
    for texto in (p.guion, p.whatsapp, p.tarjeta_titulo, p.tarjeta_introduccion,
                  p.seccion_razon, p.seccion_accion, p.asistente_individual,
                  p.asistente_catalogo, "Su familia podría calificar."):
        assert not contiene_promesa(texto), texto
