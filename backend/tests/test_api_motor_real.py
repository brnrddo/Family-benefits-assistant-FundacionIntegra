"""Tests del motor real detrás de ``E3_MOCK=0`` (B1).

La API sirve el precálculo del Rol 1 (``build_views`` sobre una copia de la DB
de prueba, fixture ``db_motor_path``) con el C4 YAML del Rol 4 (``content/``).
Cada respuesta se valida contra el schema C3 de su ruta y se compara con el
motor (``evaluar_acceso_familia``) para demostrar que la API no altera nada.

Todo el material es sintético (``SYNTHETIC_DEMO_NOT_A_REAL_PERSON``).
"""
from __future__ import annotations

import copy
import dataclasses
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.access.model import EstadoAcceso  # noqa: E402
from app.access.service import AccesoService, evaluar_acceso_familia  # noqa: E402
from app.api import motor_real, runtime  # noqa: E402
from app.api.app import app  # noqa: E402
from app.api.deps import (  # noqa: E402
    CONTENT_BUNDLE_HASH,
    CONTENT_VERSION,
    DISCLAIMER,
    ELIGIBILITY_BUNDLE_HASH,
    SNAPSHOT_ID,
)
from app.api.models import validar_benefit_result, validar_opportunity  # noqa: E402
from app.api.routers import tracking  # noqa: E402
from app.api.serializers import familia_detail_data  # noqa: E402
from app.engine.model import Nivel, Tri  # noqa: E402
from app.priority import content_c4  # noqa: E402
from app.priority.content_c4 import cargar_contenido_c4  # noqa: E402
from app.priority.orden import grupo_accion  # noqa: E402
from app.priority.scoring import OpportunityScore, family_priority_score  # noqa: E402
from tests.c3_schema import validar, validar_error  # noqa: E402

client = TestClient(app)

_FAMILIA = "FAM-SIM-E3-00001"
_MUESTRA = ["FAM-SIM-E3-00001", "FAM-SIM-E3-00002", "FAM-SIM-E3-00137",
            "FAM-SIM-E3-00250", "FAM-SIM-E3-00500"]
_SIN_CITA = ("BEN-018", "BEN-019", "BEN-020")  # PREG-045
_RESULTADO_TRAZA = {"SI": "CUMPLE", "NO": "NO_CUMPLE", "INDETERMINADO": "INDETERMINADO"}


@pytest.fixture(scope="module", autouse=True)
def _cache_limpio():
    motor_real.limpiar_cache()
    yield
    motor_real.limpiar_cache()


@pytest.fixture(autouse=True)
def _modo_real(monkeypatch, db_motor_path: Path):
    """``E3_MOCK=0`` contra la DB con precálculo y sin conversaciones previas."""
    monkeypatch.setenv("E3_MOCK", "0")
    monkeypatch.setattr(runtime, "DB_PATH", db_motor_path)
    monkeypatch.setattr(tracking, "_IDEMPOTENCIA", {})


@pytest.fixture()
def snap() -> motor_real.MotorSnapshot:
    s = motor_real.obtener_snapshot()
    assert s is not None, "el motor real debe estar disponible con precálculo"
    return s


@pytest.fixture()
def motor_conn(db_motor_path: Path):
    c = sqlite3.connect(db_motor_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def _get(path: str, **params) -> dict:
    r = client.get(f"/api/v1{path}", params=params or None)
    assert r.status_code == 200, r.status_code
    return r.json()


# --- incremento 1: ficha y oportunidades -------------------------------------


@pytest.mark.parametrize("family_id", _MUESTRA)
def test_ficha_real_valida_c3(family_id: str, motor_conn):
    body = _get(f"/familias/{family_id}")
    validar("FamiliaDetailEnvelope", body)
    data = body["data"]
    assert data["family_id"] == family_id
    assert data["disclaimer"] == DISCLAIMER
    assert data["informed"] is False
    jardin = motor_conn.execute(
        "SELECT id_jardin FROM familias WHERE id_familia = ?", (family_id,)
    ).fetchone()[0]
    assert data["garden_id"] == jardin
    n_beneficios = motor_conn.execute("SELECT COUNT(*) FROM beneficios").fetchone()[0]
    assert len(data["benefit_results"]) == n_beneficios
    assert [b["benefit_id"] for b in data["benefit_results"]] == sorted(
        b["benefit_id"] for b in data["benefit_results"]
    )
    assert body["meta"]["snapshot_id"] == SNAPSHOT_ID


@pytest.mark.parametrize("family_id", _MUESTRA)
@pytest.mark.parametrize("orden", ["prioridad", "urgencia", "beneficio"])
def test_oportunidades_reales_validan_c3(family_id: str, orden: str):
    body = _get(f"/familias/{family_id}/oportunidades", orden=orden, limit=100)
    validar("OpportunityListEnvelope", body)
    assert body["items"], "toda familia del dataset tiene oportunidades"
    assert body["next_cursor"] is None


def _comparar_con_motor(family_id: str, resultados_motor) -> None:
    ficha = _get(f"/familias/{family_id}")["data"]
    opps = _get(f"/familias/{family_id}/oportunidades", limit=100)["items"]
    por_id = {b["benefit_id"]: b for b in ficha["benefit_results"]}
    contenido = cargar_contenido_c4()
    esperadas = set()
    for acc in resultados_motor:
        elig = acc.elegibilidad
        br = por_id[acc.id_beneficio]
        assert br["result"] == elig["resultado"]
        assert br["level"] == elig["nivel"]
        assert br["access_state"] == acc.estado.value
        faltantes = list(dict.fromkeys(elig["datos_faltantes"]))[:20]
        assert br["missing_codes"] == faltantes
        assert [t["rule_id"] for t in br["trace"]] == [t["id_regla"] for t in elig["traza"]]
        assert [t["field"] for t in br["trace"]] == [t["campo"] for t in elig["traza"]]
        assert [t["operator"] for t in br["trace"]] == [t["operador"] for t in elig["traza"]]
        assert [t["result"] for t in br["trace"]] == [
            _RESULTADO_TRAZA[t["resultado"]] for t in elig["traza"]
        ]
        if (
            elig["resultado"] in ("SI", "INDETERMINADO")
            and contenido.beneficios[acc.id_beneficio].official_url is not None
        ):
            esperadas.add(acc.id_beneficio)
    assert {o["benefit_id"] for o in opps} == esperadas
    for o in opps:
        br = por_id[o["benefit_id"]]
        assert (o["result"], o["level"], o["access_state"]) == (
            br["result"], br["level"], br["access_state"]
        )
        assert o["missing_codes"] == br["missing_codes"]


def test_api_coincide_con_evaluar_acceso_familia(motor_conn):
    """La ficha de una familia concreta es exactamente la salida del motor."""
    _comparar_con_motor(_FAMILIA, evaluar_acceso_familia(_FAMILIA, motor_conn))


def test_api_coincide_con_motor_en_otras_familias(motor_conn):
    svc = AccesoService(motor_conn)  # lo mismo que evaluar_acceso_familia, un solo cupo
    for family_id in ("FAM-SIM-E3-00137", "FAM-SIM-E3-00500"):
        _comparar_con_motor(family_id, svc.evaluar_familia(family_id))


def test_invariantes_y_c3_en_las_500(snap: motor_real.MotorSnapshot):
    meta = _get("/jardines")["meta"]
    assert len(snap.familias) == 500
    for family_id, fam in snap.familias.items():
        data = familia_detail_data(motor_real.vista_familia(snap, family_id, False))
        validar("FamilyDetail", data)
        for br in data["benefit_results"]:
            validar_benefit_result(br["result"], br["level"], br["access_state"])
            if br["result"] in ("NO", "NO_APLICA"):
                assert br["level"] is None and br["access_state"] == "NO_APLICA"
        opps = motor_real.oportunidades(snap, family_id, "prioridad")
        validar("OpportunityListEnvelope", {"meta": meta, "items": opps, "next_cursor": None})
        for o in opps:
            validar_opportunity(o["result"], o["level"], o["access_state"])
            assert o["result"] in ("SI", "INDETERMINADO")
            if o["result"] == "SI":
                assert o["level"] in ("CONFIRMADO", "PRELIMINAR")
            else:
                assert o["level"] is None and o["access_state"] == "INDETERMINADO"
        assert [o["position"] for o in opps] == list(range(1, len(opps) + 1))
        assert data["top_opportunities"] == opps[:3]


def test_orden_por_grupo_de_accion_y_prioridad_familiar(snap: motor_real.MotorSnapshot):
    """DEC-053 define position/top; family_priority_score sigue usando el score."""
    cfg = cargar_contenido_c4().ranking
    for family_id, fam in snap.familias.items():
        opps = fam["opportunities"]
        grupos = [grupo_accion(EstadoAcceso(o["access_state"])) for o in opps]
        assert grupos == sorted(grupos)
        assert fam["summary"]["top_benefit_ids"] == [o["benefit_id"] for o in opps[:3]]
        por_score = sorted(
            (
                OpportunityScore(
                    benefit_id=o["benefit_id"], result=Tri(o["result"]),
                    level=Nivel(o["level"]) if o["level"] else None,
                    access_state=EstadoAcceso(o["access_state"]), urgency=o["urgency"],
                    benefit=o["benefit"], vulnerability=o["vulnerability"], score=o["score"],
                    position=0, estimated_annual_amount=o["estimated_annual_amount"],
                    benefit_estimated=o["benefit_estimated"],
                )
                for o in opps
            ),
            key=lambda s: (-s.score, -s.urgency, -s.benefit, s.benefit_id),
        )
        esperado = family_priority_score(por_score, cfg, conversada=False)
        assert fam["summary"]["priority_score"] == pytest.approx(esperado.priority_score)


def test_ordenes_vista_y_paginacion():
    base = f"/familias/{_FAMILIA}/oportunidades"
    completa = _get(base, limit=100)["items"]
    assert [o["position"] for o in completa] == list(range(1, len(completa) + 1))
    for orden, eje in (("urgencia", "urgency"), ("beneficio", "benefit")):
        items = _get(base, orden=orden, limit=100)["items"]
        assert {o["benefit_id"] for o in items} == {o["benefit_id"] for o in completa}
        claves = [(grupo_accion(EstadoAcceso(o["access_state"])), -o[eje], o["position"])
                  for o in items]
        assert claves == sorted(claves)

    # Paginación estable por cursor opaco.
    vistos: list[str] = []
    cursor = None
    while True:
        params = {"limit": 4} | ({"cursor": cursor} if cursor else {})
        body = _get(base, **params)
        validar("OpportunityListEnvelope", body)
        vistos += [o["benefit_id"] for o in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert vistos == [o["benefit_id"] for o in completa]


@pytest.mark.parametrize("plantilla", [
    "basura", "SNAP-OTRO:{h}:4", "{s}:{h}:0", "{s}:{h}:999", "{s}:{h}:-1",
    "{s}:4",                     # formato sin huella (iteración 1)
    "{s}:0000000000000000:4",    # huella de otro build
    "{s}:{h}:4:extra",
])
def test_cursor_invalido_422(plantilla: str, snap: motor_real.MotorSnapshot):
    cursor = plantilla.format(s=SNAPSHOT_ID, h=snap.huella)
    r = client.get(f"/api/v1/familias/{_FAMILIA}/oportunidades", params={"cursor": cursor})
    assert r.status_code == 422
    validar_error(r.json())


def test_cursor_lleva_huella_del_snapshot(snap: motor_real.MotorSnapshot):
    cursor = _get(f"/familias/{_FAMILIA}/oportunidades", limit=4)["next_cursor"]
    assert cursor == f"{SNAPSHOT_ID}:{snap.huella}:4"
    assert re.fullmatch(r"[0-9a-f]{16}", snap.huella)


def test_orden_invalido_422():
    r = client.get(f"/api/v1/familias/{_FAMILIA}/oportunidades", params={"orden": "ZZZ"})
    assert r.status_code == 422
    validar_error(r.json())


@pytest.mark.parametrize("family_id", ["FAM-SIM-0001", "FAM-SIM-E3-99999"])
@pytest.mark.parametrize("sufijo", ["", "/oportunidades"])
def test_familia_inexistente_404(family_id: str, sufijo: str):
    """Los IDs mock y los inexistentes no existen en modo real."""
    r = client.get(f"/api/v1/familias/{family_id}{sufijo}")
    assert r.status_code == 404
    validar_error(r.json())


def test_citas_y_monto_preg045_preg048(snap: motor_real.MotorSnapshot):
    for fam in snap.familias.values():
        ids_br = {b["benefit_id"] for b in fam["benefit_results"]}
        assert set(_SIN_CITA) <= ids_br
        for o in fam["opportunities"]:
            assert o["benefit_id"] not in _SIN_CITA
            assert o["sources"]
            assert all(s["url"].startswith("https://") for s in o["sources"])
            if o["estimated_annual_amount"] is None:
                assert o["benefit_estimated"] is True


def test_presentacion_y_ranking_salen_de_content(snap: motor_real.MotorSnapshot):
    """Ajuste (A): título, dónde ir, cita, preguntas y medianas vienen de content/."""
    contenido = cargar_contenido_c4()
    con_mediana = 0
    for fam in snap.familias.values():
        for o in fam["opportunities"]:
            cat = contenido.beneficios[o["benefit_id"]]
            assert o["simple_title"] == cat.simple_title
            assert o["where_to_go"] == cat.where_to_go
            assert o["sources"] == [{"source_id": cat.official_source_id,
                                     "url": cat.official_url}]
            for q in o["suggested_questions"]:
                assert q in contenido.preguntas.values()
            if o["estimated_annual_amount"] is not None and not o["benefit_estimated"]:
                con_mediana += 1  # solo posible con la mediana del jardín de C4
    assert con_mediana > 0


# "Nunca prometer" (fuente funcional §2.4.2 y §9.1, CONT-003, DEC-054 de GenAI).
_PROMESAS = re.compile(
    r"\b(tienen? derecho|recibirán?|les? corresponden?|corresponderles?|garantiza\w*"
    r"|asegurad[oa]s?|califican?|es elegible|son elegibles|cumplen?)\b"
)
# Estados con SI que el copy debe matizar con "podría" (ASIGNADO y
# GESTION_EN_CURSO describen hechos del dato).
_ESTADOS_PODRIA = ("ELEGIBLE_SIN_ASIGNACION", "PENDIENTE_ANTECEDENTES",
                   "GESTION_RECHAZADA", "SIN_CUPO", "INDETERMINADO")


def test_why_first_no_promete_ni_da_cifras(snap: motor_real.MotorSnapshot):
    tabla = motor_real._WHY_FIRST
    # Un texto por cada estado que admite Opportunity en C3.
    assert set(tabla) == {e.value for e in EstadoAcceso} - {"NO_APLICA"}
    for estado, texto in tabla.items():
        assert 1 <= len(texto) <= 240
        assert not _PROMESAS.search(texto.lower()), estado
        assert not re.search(r"\d|\$", texto), estado
        if estado in _ESTADOS_PODRIA:
            assert "podría" in texto.lower(), estado
        # CONT-003: frases de 20 palabras como máximo.
        for frase in re.split(r"[.:;]", texto):
            assert len(frase.split()) <= 20, estado
    for fam in snap.familias.values():
        for o in fam["opportunities"]:
            assert o["why_first"] == tabla[o["access_state"]]


# --- incremento 2: contexto minimizado ----------------------------------------


@pytest.mark.parametrize("family_id", _MUESTRA)
def test_contexto_real_valida_c3(family_id: str):
    body = _get(f"/familias/{family_id}/contexto")
    validar("FamiliaContextEnvelope", body)
    assert body["data"]["family_id"] == family_id
    ficha = _get(f"/familias/{family_id}")["data"]
    assert body["data"]["composition"] == ficha["composition"]
    assert body["data"]["rsh_band"] == ficha["rsh_band"]


def test_contexto_de_las_500_valida_c3(snap: motor_real.MotorSnapshot):
    for family_id in snap.familias:
        validar("FamilyContextView", motor_real.contexto(snap, family_id))


def test_contexto_mapea_c2_por_allowlist(snap: motor_real.MotorSnapshot, motor_conn):
    from app.context import construir_contexto

    cfg = cargar_contenido_c4().ranking
    ingreso = {"MENOS_110K": "UNDER_110K", "ENTRE_110K_250K": "110K_250K",
               "ENTRE_250K_400K": "250K_400K", "MAS_400K": "OVER_400K"}
    sin_tramo = 0
    for family_id in snap.familias:
        ctx = motor_real.contexto(snap, family_id)
        c2 = construir_contexto(family_id, motor_conn)
        assert ctx["income_band"] == ingreso.get(c2["ingreso_per_capita_rango"])
        assert len(ctx["composition"]) == len(c2["composicion"])
        if c2["rsh"]["tramo"] is None:
            sin_tramo += 1
            assert ctx["rsh_band"] is None
            assert "rsh_band" in ctx["missing_codes"]
            # Sin RSH confirmado -> no_rsh; RSH desconocido (no_informado) -> null.
            sin_rsh = c2["rsh"]["tiene"] is False and "tramo_rsh" not in c2["no_informado"]
            esperado = cfg.vulnerability["rsh_scores"]["no_rsh"] if sin_rsh else None
            assert ctx["vulnerability_signals"]["rsh_score"] == esperado
        else:
            assert ctx["rsh_band"] == c2["rsh"]["tramo"]
            assert ctx["vulnerability_signals"]["rsh_score"] == (
                cfg.vulnerability["rsh_scores"][f"band_{ctx['rsh_band']}"]
            )
        if ctx["income_band"] is not None:
            assert ctx["vulnerability_signals"]["income_score"] == (
                cfg.vulnerability["income_band_scores"][ctx["income_band"]]
            )
        assert ctx["urgency_signals"]["recent_emergency"] == c2["senales_urgencia"][
            "evento_emergencia"]
        assert ctx["inconsistency_codes"] == []
    assert sin_tramo > 0, "el dataset trae familias sin tramo RSH"


_PROHIBIDOS = ("folio", "FOLIO-RSH-SIM", "identificador_mod11", "SIM-9", "PER-SIM-",
               "fecha_nacimiento", "nombre_comuna", "Comuna Sintética", "nacionalidad",
               "id_integrante", "ANT-SIM-")


def _sin_prohibidos(payload) -> None:
    from app.context.context_filter import contiene_campo_prohibido

    texto = json.dumps(payload, ensure_ascii=False)
    for marca in _PROHIBIDOS:
        assert marca not in texto, marca
    assert contiene_campo_prohibido(payload) == []


def test_privacidad_respuestas_reales(snap: motor_real.MotorSnapshot):
    """Ningún dato excluido ni local de la tía llega a las respuestas (DEC-038)."""
    for family_id in _MUESTRA:
        for path in ("", "/contexto", "/oportunidades"):
            _sin_prohibidos(_get(f"/familias/{family_id}{path}"))
    _sin_prohibidos(_get("/jardines", limit=100))
    for family_id in snap.familias:
        _sin_prohibidos(familia_detail_data(motor_real.vista_familia(snap, family_id, False)))
        _sin_prohibidos(motor_real.contexto(snap, family_id))


# --- incremento 3: jardines, familias por jardín, conversaciones --------------

_DATA_DIR = BACKEND_DIR.parent / "data" / "publico"


def _ids_csv(nombre: str, columna: str) -> set[str]:
    import csv

    with (_DATA_DIR / nombre).open(encoding="utf-8", newline="") as fh:
        return {row[columna] for row in csv.DictReader(fh)}


def _conversacion(family_id: str, origin: str = "REAL_DEMO", key: str | None = None):
    import uuid

    return client.post(
        f"/api/v1/familias/{family_id}/conversaciones",
        json={
            "benefit_ids": ["BEN-001"],
            "next_step": "GO_TO_INSTITUTION",
            "channel": "IN_PERSON",
            "occurred_at": "2026-10-13T12:00:00Z",
            "snapshot_id": SNAPSHOT_ID,
            "origin": origin,
        },
        headers={"Idempotency-Key": key or str(uuid.uuid4())},
    )


def _paginas(path: str, limit: int, entre_paginas=None) -> list[dict]:
    cuerpos: list[dict] = []
    cursor = None
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        body = _get(path, **params)
        cuerpos.append(body)
        cursor = body["next_cursor"]
        if cursor is None:
            return cuerpos
        if entre_paginas is not None:
            entre_paginas()


def test_jardines_reales_una_pagina_de_100():
    body = _get("/jardines", limit=100)
    validar("JardinListEnvelope", body)
    assert body["next_cursor"] is None
    ids = [j["garden_id"] for j in body["items"]]
    assert ids == sorted(ids)
    assert set(ids) == _ids_csv("jardines.csv", "id_jardin")
    assert all("-SIM-" in g for g in ids)
    assert sum(j["families_total"] for j in body["items"]) == 500
    assert all(j["families_informed"] == 0 and j["informed_percentage"] == 0.0
               for j in body["items"])


def test_jardines_paginados_sin_duplicados():
    paginas = _paginas("/jardines", limit=25)
    assert len(paginas) == 2
    ids = [j["garden_id"] for p in paginas for j in p["items"]]
    assert len(ids) == len(set(ids)) == 50
    for p in paginas:
        validar("JardinListEnvelope", p)


def test_familias_por_jardin_paginadas_y_estables():
    jardin = _get("/jardines", limit=1)["items"][0]["garden_id"]
    path = f"/jardines/{jardin}/familias"
    completa = _get(path, limit=100)["items"]

    def _registrar():
        assert _conversacion(completa[0]["family_id"]).status_code == 201

    paginas = _paginas(path, limit=3, entre_paginas=_registrar)
    assert len(paginas) == 4
    ids = [f["family_id"] for p in paginas for f in p["items"]]
    assert ids == [f["family_id"] for f in completa]  # orden estable aun con conversación
    assert len(set(ids)) == 10
    assert {p["meta"]["snapshot_id"] for p in paginas} == {SNAPSHOT_ID}
    familias_csv = _ids_csv("familias.csv", "id_familia")
    for p in paginas:
        validar("FamiliaListEnvelope", p)
        for f in p["items"]:
            assert "-SIM-" in f["family_id"] and f["family_id"] in familias_csv


def test_tarjeta_coherente_con_oportunidades():
    jardin = _get("/jardines", limit=1)["items"][0]["garden_id"]
    for tarjeta in _get(f"/jardines/{jardin}/familias", limit=100)["items"]:
        opps = _get(f"/familias/{tarjeta['family_id']}/oportunidades", limit=100)["items"]
        assert tarjeta["opportunity_count"] == len(opps)
        assert tarjeta["top_benefit_ids"] == [o["benefit_id"] for o in opps[:3]]
        assert tarjeta["conversation_status"] == "PENDIENTE"
        colores = {
            "ELEGIBLE_SIN_ASIGNACION": "VERDE", "GESTION_RECHAZADA": "VERDE",
            "PENDIENTE_ANTECEDENTES": "AMARILLO", "INDETERMINADO": "AMARILLO",
            "SIN_CUPO": "AMARILLO", "ASIGNADO": "AZUL", "GESTION_EN_CURSO": "AZUL",
        }
        presentes = {colores[o["access_state"]] for o in opps}
        esperado = next((c for c in ("VERDE", "AMARILLO", "AZUL") if c in presentes),
                        "SIN_OPORTUNIDADES")
        assert tarjeta["traffic_light"] == esperado


def test_conversacion_real_marca_informada(snap: motor_real.MotorSnapshot):
    garden_id = snap.familias[_FAMILIA]["garden_id"]
    antes = next(j for j in _get("/jardines", limit=100)["items"] if j["garden_id"] == garden_id)
    r = _conversacion(_FAMILIA, origin="REAL_DEMO")
    assert r.status_code == 201
    validar("ConversationEnvelope", r.json())
    assert r.json()["data"]["garden_id"] == garden_id

    assert _get(f"/familias/{_FAMILIA}")["data"]["informed"] is True
    tarjeta = next(f for f in _get(f"/jardines/{garden_id}/familias", limit=100)["items"]
                   if f["family_id"] == _FAMILIA)
    assert tarjeta["conversation_status"] == "CONVERSADA"
    pendiente, conversada = snap.prioridades[_FAMILIA]
    assert tarjeta["priority_score"] == conversada != pendiente
    despues = next(j for j in _get("/jardines", limit=100)["items"]
                   if j["garden_id"] == garden_id)
    assert despues["families_informed"] == antes["families_informed"] + 1
    assert despues["informed_percentage"] > antes["informed_percentage"]


def test_conversacion_simulada_y_mock_id(snap):
    assert _conversacion("FAM-SIM-E3-00002", origin="SIMULADO_DEMO").status_code == 201
    r = _conversacion("FAM-SIM-0001")
    assert r.status_code == 404
    validar_error(r.json())


@pytest.mark.parametrize("ruta,schema", [("guion", "ScriptGenerationEnvelope"),
                                         ("mensaje", "MessageGenerationEnvelope")])
def test_guion_y_mensaje_con_id_real(ruta: str, schema: str):
    r = client.post(f"/api/v1/familias/{_FAMILIA}/{ruta}", json={"benefit_ids": ["BEN-001"]})
    assert r.status_code == 200
    validar(schema, r.json())
    r404 = client.post(f"/api/v1/familias/FAM-SIM-0001/{ruta}", json={"benefit_ids": ["BEN-001"]})
    assert r404.status_code == 404
    validar_error(r404.json())


@pytest.mark.parametrize("ruta,schema", [("guion", "ScriptGenerationEnvelope"),
                                         ("mensaje", "MessageGenerationEnvelope")])
def test_guion_y_mensaje_con_top_real_no_sustituyen_beneficios(ruta: str, schema: str):
    """Con el top real de una familia, el texto habla de esos beneficios y no de otro.

    Regresión: con el catálogo mock de tres beneficios, BEN-011 (fuera del mock)
    recibía el texto de BEN-001 con ``FALLBACK_TEMPLATE``.
    """
    import yaml

    top = [o["benefit_id"] for o in _get(f"/familias/{_FAMILIA}")["data"]["top_opportunities"]]
    assert top, "la familia de prueba debe tener oportunidades"
    with (BACKEND_DIR.parent / "content" / "beneficios.yaml").open(encoding="utf-8") as fh:
        titulos = {b["benefit_id"]: b["simple_title"] for b in yaml.safe_load(fh)["beneficios"]}

    r = client.post(f"/api/v1/familias/{_FAMILIA}/{ruta}", json={"benefit_ids": top})
    assert r.status_code == 200
    body = r.json()
    validar(schema, body)
    assert body["content"]["benefit_ids"] == top
    assert "FALLBACK_TEMPLATE" not in body["warnings"]
    texto = body["content"]["script"] if ruta == "guion" else body["content"]["whatsapp_preview"]
    for bid in top:
        assert titulos[bid] in texto
    for bid, titulo in titulos.items():
        if bid not in top:
            assert titulo not in texto


def test_meta_declara_procedencia_de_content(monkeypatch):
    """DEC-062: ficha real y guion declaran el bundle ``content/``; el mock no."""
    import yaml

    manifest = yaml.safe_load(Path(content_c4.CONTENT_MANIFEST).read_text(encoding="utf-8"))
    procedencia = (manifest["content_version"], manifest["content_bundle_hash"])
    assert procedencia[0] == "0.2.1"

    def _de(meta: dict) -> tuple[str, str]:
        assert meta["snapshot_id"] == SNAPSHOT_ID
        assert meta["eligibility_bundle_hash"] == ELIGIBILITY_BUNDLE_HASH
        return meta["content_version"], meta["content_bundle_hash"]

    ficha = _get(f"/familias/{_FAMILIA}")  # E3_MOCK=0: snapshot del motor real
    validar("FamiliaDetailEnvelope", ficha)
    assert _de(ficha["meta"]) == procedencia

    monkeypatch.setenv("E3_MOCK", "1")
    monkeypatch.setattr(runtime, "_provider", None)
    r = client.post("/api/v1/familias/FAM-SIM-0001/guion", json={"benefit_ids": ["BEN-001"]})
    assert r.status_code == 200
    validar("ScriptGenerationEnvelope", r.json())
    assert _de(r.json()["meta"]) == procedencia
    assert _de(_get("/jardines")["meta"]) == (CONTENT_VERSION, CONTENT_BUNDLE_HASH)


def test_antecedentes_real_404_y_503():
    import uuid

    cuerpo = {"data_classification": "SYNTHETIC_DEMO_NOT_A_REAL_PERSON", "has_rsh": True}
    r = client.post("/api/v1/familias/FAM-SIM-E3-99999/antecedentes", json=cuerpo,
                    headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 404
    validar_error(r.json())
    r = client.post(f"/api/v1/familias/{_FAMILIA}/antecedentes", json=cuerpo,
                    headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 503
    validar_error(r.json())
    assert r.json()["error"]["retryable"] is True


@pytest.mark.parametrize("path", ["/jardines", "/jardines/JAR-SIM-E3-00001/familias"])
def test_cursor_invalido_en_listas_422(path: str):
    r = client.get(f"/api/v1{path}", params={"cursor": "SNAP-OTRO:3"})
    assert r.status_code == 422
    validar_error(r.json())


@pytest.mark.parametrize("garden_id", ["JARDIN-001", "JAR-SIM-E3-99999"])
def test_jardin_inexistente_404(garden_id: str):
    r = client.get(f"/api/v1/jardines/{garden_id}/familias")
    assert r.status_code == 404
    validar_error(r.json())


def test_check_api_en_python():
    """Misma cadena que ``frontend/scripts/check-api.mjs`` con los schemas C3."""
    jardines = _get("/jardines", limit=100)
    validar("JardinListEnvelope", jardines)
    garden_id = jardines["items"][0]["garden_id"]
    familias = _get(f"/jardines/{garden_id}/familias")
    validar("FamiliaListEnvelope", familias)
    family_id = familias["items"][0]["family_id"]
    validar("FamiliaDetailEnvelope", _get(f"/familias/{family_id}"))
    validar("FamiliaContextEnvelope", _get(f"/familias/{family_id}/contexto"))
    for orden in ("prioridad", "urgencia", "beneficio"):
        validar("OpportunityListEnvelope", _get(f"/familias/{family_id}/oportunidades",
                                                orden=orden))
    validar("KpiEnvelope", _get("/kpi", nivel="nacional"))
    validar("KpiEnvelope", _get("/kpi", nivel="jardin", id=garden_id))


# --- degradación ---------------------------------------------------------------


def _avisos(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)


@pytest.fixture(autouse=True)
def _sin_fallo_previo(monkeypatch):
    """Olvida el último fallo cacheado (no el snapshot): cada test ve su warning."""
    monkeypatch.setattr(motor_real, "_FALLO", None)


def test_sin_precalculo_degrada_a_mock_con_warning(monkeypatch, db_path: Path, caplog):
    monkeypatch.setattr(runtime, "DB_PATH", db_path)  # solo loader, sin build_views
    with caplog.at_level(logging.WARNING, logger="app.api"):
        ficha = client.get("/api/v1/familias/FAM-SIM-0001")
        opps = client.get("/api/v1/familias/FAM-SIM-0001/oportunidades")
    assert ficha.status_code == 200 and opps.status_code == 200
    validar("FamiliaDetailEnvelope", ficha.json())
    validar("OpportunityListEnvelope", opps.json())
    avisos = _avisos(caplog)
    assert "motivo=PRECALCULO_AUSENTE" in avisos
    assert "FAM-" not in avisos and "JAR-" not in avisos


def test_db_inexistente_degrada_a_mock_sin_500(monkeypatch, tmp_path: Path, caplog):
    monkeypatch.setattr(runtime, "DB_PATH", tmp_path / "no_existe.db")
    with caplog.at_level(logging.WARNING, logger="app.api"):
        assert client.get("/api/v1/familias/FAM-SIM-0001").status_code == 200
        assert client.get("/api/v1/familias/FAM-SIM-0001/oportunidades").status_code == 200
        # El mock no conoce los IDs reales: 404, nunca 500.
        assert client.get(f"/api/v1/familias/{_FAMILIA}").status_code == 404
    assert "motivo=DB_AUSENTE" in _avisos(caplog)


def test_db_corrupta_degrada_a_mock(monkeypatch, tmp_path: Path, caplog):
    db = tmp_path / "corrupta.db"
    db.write_bytes(b"esto no es sqlite" * 64)
    monkeypatch.setattr(runtime, "DB_PATH", db)
    with caplog.at_level(logging.WARNING, logger="app.api"):
        assert client.get("/api/v1/familias/FAM-SIM-0001").status_code == 200
    assert "motivo=DB_ILEGIBLE" in _avisos(caplog)


def test_c4_invalido_degrada_a_mock(monkeypatch, tmp_path: Path, caplog):
    monkeypatch.setattr(content_c4, "CONTENT_MANIFEST", tmp_path / "content" / "manifest.yaml")
    with caplog.at_level(logging.WARNING, logger="app.api"):
        assert client.get("/api/v1/familias/FAM-SIM-0001").status_code == 200
    assert "motivo=C4_INVALIDO" in _avisos(caplog)


def test_e3_mock_1_ignora_el_motor(monkeypatch):
    monkeypatch.setenv("E3_MOCK", "1")
    assert motor_real.obtener_snapshot() is None
    assert client.get("/api/v1/familias/FAM-SIM-0001").status_code == 200
    assert client.get(f"/api/v1/familias/{_FAMILIA}").status_code == 404


def test_log_de_request_usa_ruta_normalizada(caplog):
    with caplog.at_level(logging.INFO, logger="app.api"):
        _get(f"/familias/{_FAMILIA}")
        _get(f"/familias/{_FAMILIA}/oportunidades")
    assert "path=/api/v1/familias/{id} status=200" in caplog.text
    assert "path=/api/v1/familias/{id}/oportunidades status=200" in caplog.text
    assert _FAMILIA not in caplog.text and "FAM-SIM-E3" not in caplog.text


def test_arranque_precalienta_y_nunca_rompe(monkeypatch, tmp_path: Path):
    with TestClient(app) as c:  # ejecuta el lifespan con el motor real disponible
        assert c.get("/healthz").status_code == 200
    monkeypatch.setattr(runtime, "DB_PATH", tmp_path / "no_existe.db")
    with TestClient(app) as c:  # sin DB: el arranque sigue y las rutas degradan
        assert c.get("/healthz").status_code == 200
        assert c.get("/api/v1/familias/FAM-SIM-0001").status_code == 200


def test_build_del_snapshot_bajo_30_s():
    motor_real.limpiar_cache()
    inicio = time.perf_counter()
    snap = motor_real.obtener_snapshot()
    segundos = time.perf_counter() - inicio
    print(f"\nbuild del snapshot: {segundos:.2f} s (interno {snap.segundos_build:.2f} s)")
    assert snap is not None
    assert segundos < 30


def test_salidas_por_request_no_comparten_estado_con_el_snapshot(snap: motor_real.MotorSnapshot):
    """Mutar lo que devuelven los helpers (lo que serializa la ruta) no toca el snapshot."""
    garden_id = snap.familias[_FAMILIA]["garden_id"]
    familia_antes = copy.deepcopy(snap.familias[_FAMILIA])
    jardin_antes = copy.deepcopy(snap.jardines[garden_id])

    ficha = familia_detail_data(motor_real.vista_familia(snap, _FAMILIA, False))
    ficha["benefit_results"][0]["missing_codes"].append("mutado")
    ficha["benefit_results"][0]["trace"].clear()
    ficha["top_opportunities"][0]["sources"][0]["url"] = "https://mutado.invalid"
    ficha["composition"].clear()
    opps = motor_real.oportunidades(snap, _FAMILIA, "prioridad")
    opps[0]["missing_codes"].append("mutado")
    opps[0]["suggested_questions"].append("mutado")
    opps.clear()
    ctx = motor_real.contexto(snap, _FAMILIA)
    ctx["missing_codes"].append("mutado")
    ctx["urgency_signals"]["recent_emergency"] = "mutado"
    resumen = motor_real.resumen_familia(snap, _FAMILIA, True)
    resumen["top_benefit_ids"].append("BEN-MUTADO")
    jardin = motor_real.resumen_jardin(snap, garden_id, frozenset())
    jardin["families_total"] = -1

    assert snap.familias[_FAMILIA] == familia_antes
    assert snap.jardines[garden_id] == jardin_antes
    for path in ("", "/contexto", "/oportunidades"):
        assert "mutado" not in json.dumps(_get(f"/familias/{_FAMILIA}{path}"))


# --- iteración 2: hallazgos de la revisión --------------------------------------


def test_contexto_sin_rsh_usa_no_rsh_y_desconocido_queda_null():
    """Rama ``has_rsh=False`` -> ``no_rsh``; RSH no informado -> ``null`` (DEC-049)."""
    cfg = cargar_contenido_c4().ranking
    c2 = {  # C2 sintético mínimo (SYNTHETIC_DEMO_NOT_A_REAL_PERSON)
        "composicion": [{"rol": "ADULTA_REFERENCIA", "edad": 30},
                        {"rol": "HIJO_HIJA", "edad": 3}],
        "no_informado": [],
        "rsh": {"tiene": False, "tramo": None},
        "ingreso_per_capita_rango": "MENOS_110K",
        "formato_preferido": "TEXTO",
        "idioma_mensaje": "es",
        "posible_discapacidad_nino": "NO_INFORMADO",
        "senales_urgencia": {"evento_emergencia": False, "inseguridad_alimentaria": None},
    }
    vista, _, senales_v = motor_real._contexto_c3("FAM-SIM-TEST-1", c2, cfg)
    validar("FamilyContextView", vista)
    assert vista["rsh_band"] is None
    assert vista["vulnerability_signals"]["rsh_score"] == cfg.vulnerability["rsh_scores"]["no_rsh"]
    assert senales_v.has_rsh is False

    desconocido = {**c2, "no_informado": ["tramo_rsh"]}
    vista, _, senales_v = motor_real._contexto_c3("FAM-SIM-TEST-2", desconocido, cfg)
    validar("FamilyContextView", vista)
    assert vista["vulnerability_signals"]["rsh_score"] is None
    assert senales_v.has_rsh is None
    assert "rsh_band" in vista["missing_codes"]


def test_preguntas_resolubles_cuentan_solo_codigos_con_pregunta(monkeypatch, db_motor_path: Path):
    """``resolvable_question_count`` = preguntas distintas de C4, no faltantes brutos."""
    from app.context import ContextoBuilder

    contenido = cargar_contenido_c4()
    capturadas = []
    original = motor_real.score_opportunities

    def espia(entradas, *args, **kwargs):
        capturadas.extend(entradas)
        return original(entradas, *args, **kwargs)

    monkeypatch.setattr(motor_real, "score_opportunities", espia)
    conn = motor_real._conectar_solo_lectura(db_motor_path)
    try:
        datos = motor_real._leer_precalculo(conn)
        c2 = ContextoBuilder(conn, datos.fecha).build(_FAMILIA)
        garden_id = dict(datos.familias)[_FAMILIA]
        familia, _, _ = motor_real._familia(_FAMILIA, garden_id, datos, c2, contenido)
    finally:
        conn.close()

    faltantes = {b["benefit_id"]: b["missing_codes"] for b in familia["benefit_results"]}
    assert capturadas
    menos_que_brutos = 0
    for e in capturadas:
        codigos = faltantes[e.benefit_id]
        esperado = len({contenido.preguntas[c] for c in codigos if c in contenido.preguntas})
        assert e.resolvable_question_count == esperado
        menos_que_brutos += e.resolvable_question_count < len(codigos)
    # La familia trae códigos sin pregunta (p. ej. DATO_ADMINISTRATIVO).
    assert menos_que_brutos > 0


def test_conversacion_resuelve_un_solo_snapshot(monkeypatch, snap: motor_real.MotorSnapshot):
    """Existencia y jardín salen del mismo snapshot aunque la DB cambie entre medio."""
    llamadas: list[int] = []

    def cambia_tras_la_primera():
        llamadas.append(1)
        return snap if len(llamadas) == 1 else None  # 2ª llamada: "DB regenerada"

    monkeypatch.setattr(motor_real, "obtener_snapshot", cambia_tras_la_primera)
    r = _conversacion(_FAMILIA)
    assert r.status_code == 201
    assert r.json()["data"]["garden_id"] == snap.familias[_FAMILIA]["garden_id"]
    assert len(llamadas) == 1

    llamadas.clear()
    r = _conversacion("FAM-SIM-0001")  # ID mock contra el snapshot real: 404, nunca 500
    assert r.status_code == 404
    validar_error(r.json())
    assert len(llamadas) == 1


def test_registro_de_conversaciones_bajo_lock(monkeypatch):
    """Lectura (GET) y escritura (POST) del registro esperan al mismo lock."""
    lock = threading.Lock()
    monkeypatch.setattr(tracking, "_LOCK_IDEMPOTENCIA", lock)
    lecturas: list[frozenset] = []
    estados: list[int] = []
    with lock:
        lector = threading.Thread(target=lambda: lecturas.append(tracking.familias_conversadas()))
        escritor = threading.Thread(target=lambda: estados.append(_conversacion(_FAMILIA).status_code))
        lector.start()
        escritor.start()
        lector.join(timeout=0.3)
        escritor.join(timeout=0.3)
        assert lector.is_alive() and escritor.is_alive()
        assert not lecturas and not estados
    lector.join(timeout=10)
    escritor.join(timeout=10)
    assert estados == [201]
    assert lecturas and lecturas[0] <= {_FAMILIA}
    assert tracking.familias_conversadas() == frozenset({_FAMILIA})


def test_access_log_de_uvicorn_sanitizado():
    """El access log de uvicorn no lleva IDs ni query, sin depender de ``--no-access-log``."""
    from app.api.app import FiltroAccessLog

    filtros = [f for f in logging.getLogger("uvicorn.access").filters
               if isinstance(f, FiltroAccessLog)]
    assert len(filtros) == 1
    filtro = filtros[0]
    # Misma forma que el ``access_logger.info`` de uvicorn (h11/httptools).
    registro = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 0, '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:50000", "GET",
         f"/api/v1/familias/{_FAMILIA}/oportunidades?orden=prioridad&cursor=X", "1.1", 200),
        None,
    )
    assert filtro.filter(registro) is True
    mensaje = registro.getMessage()
    assert '"GET /api/v1/familias/{id}/oportunidades HTTP/1.1" 200' in mensaje
    assert _FAMILIA not in mensaje and "orden" not in mensaje and "cursor" not in mensaje
    casos = {
        "/api/v1/jardines/JAR-SIM-E3-00001/familias?limit=3": "/api/v1/jardines/{id}/familias",
        "/api/v1/familias/nueva/preevaluacion": "/api/v1/familias/nueva/preevaluacion",
        "/api/v1/kpi?nivel=jardin&id=JAR-SIM-E3-00001": "/api/v1/kpi",
        "/healthz": "/healthz",
        "/": "/",
        "/otra/FAM-SIM-E3-00001": "/{id}/{id}",
    }
    for entrada, esperado in casos.items():
        assert filtro.sanitizar(entrada) == esperado
    # Un registro con otra forma pasa sin cambios.
    otro = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 0, "texto", None, None)
    assert filtro.filter(otro) is True and otro.getMessage() == "texto"


def test_cursor_de_otra_huella_responde_422(monkeypatch, snap: motor_real.MotorSnapshot):
    """El router compara el cursor contra la huella del snapshot vigente."""
    cursor = _get(f"/familias/{_FAMILIA}/oportunidades", limit=4)["next_cursor"]
    otro = dataclasses.replace(snap, huella="f" * 16)
    monkeypatch.setattr(motor_real, "obtener_snapshot", lambda: otro)
    r = client.get(f"/api/v1/familias/{_FAMILIA}/oportunidades",
                   params={"limit": 4, "cursor": cursor})
    assert r.status_code == 422
    validar_error(r.json())


# Estos dos reconstruyen el snapshot sobre copias de la DB: van al final.


def test_fallo_de_invariante_se_cachea_y_reintenta_si_cambia_la_db(
    monkeypatch, tmp_path: Path, db_motor_path: Path, caplog
):
    """INVARIANTE_MOTOR: mocks, un solo warning y un solo build por clave."""
    db = tmp_path / "invariante.db"
    shutil.copyfile(db_motor_path, db)
    c = sqlite3.connect(db)
    try:
        # SI sin nivel: combinación que C3 prohíbe (falla en la primera familia).
        n = c.execute(
            "UPDATE evaluaciones SET nivel = NULL WHERE id_familia = ? AND resultado = 'SI'",
            (_FAMILIA,),
        ).rowcount
        c.commit()
    finally:
        c.close()
    assert n > 0
    monkeypatch.setattr(runtime, "DB_PATH", db)
    builds: list[int] = []
    original = motor_real._construir

    def contar(*args):
        builds.append(1)
        return original(*args)

    monkeypatch.setattr(motor_real, "_construir", contar)
    with caplog.at_level(logging.WARNING, logger="app.api"):
        for _ in range(3):
            r = client.get("/api/v1/familias/FAM-SIM-0001")
            assert r.status_code == 200
            validar("FamiliaDetailEnvelope", r.json())
        assert client.get(f"/api/v1/familias/{_FAMILIA}").status_code == 404  # mock
    avisos = [r.getMessage() for r in caplog.records
              if r.getMessage().startswith("runtime_degradado_a_mock: motivo=")]
    assert avisos == ["runtime_degradado_a_mock: motivo=INVARIANTE_MOTOR"]
    assert "FAM-" not in _avisos(caplog)
    assert len(builds) == 1

    st = db.stat()  # la DB "cambia": se reintenta una vez
    os.utime(db, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    assert client.get("/api/v1/familias/FAM-SIM-0001").status_code == 200
    assert len(builds) == 2


def test_cursor_de_un_build_anterior_responde_422(monkeypatch, tmp_path: Path, db_motor_path: Path):
    """Regenerar la DB entre páginas invalida el cursor (422), no duplica ni salta."""
    db = tmp_path / "regenerada.db"
    shutil.copyfile(db_motor_path, db)
    monkeypatch.setattr(runtime, "DB_PATH", db)
    rutas = (f"/familias/{_FAMILIA}/oportunidades", "/jardines",
             "/jardines/JAR-SIM-E3-00001/familias")
    cursores = {p: _get(p, limit=4)["next_cursor"] for p in rutas}
    assert all(cursores.values())

    st = db.stat()  # mismo contenido, otra generación de la DB
    os.utime(db, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    for p, cursor in cursores.items():
        r = client.get(f"/api/v1{p}", params={"limit": 4, "cursor": cursor})
        assert r.status_code == 422, p
        validar_error(r.json())
        nuevo = _get(p, limit=4)["next_cursor"]
        assert nuevo != cursor
        assert _get(p, limit=4, cursor=nuevo)["items"]


def test_fallo_c4_se_recupera_al_corregir_un_archivo_de_content(
    monkeypatch, tmp_path: Path, caplog
):
    """DEC-063: corregir un archivo de ``files[]`` reconstruye sin reiniciar."""
    shutil.copytree(Path(content_c4.CONTENT_MANIFEST).parent, tmp_path / "content")
    monkeypatch.setattr(content_c4, "CONTENT_MANIFEST", tmp_path / "content" / "manifest.yaml")
    preguntas = tmp_path / "content" / "preguntas.yaml"
    original = preguntas.read_bytes()
    preguntas.write_bytes(original + b"#")  # sha256 roto; el manifest no cambia
    cargas: list[int] = []
    cargar = motor_real.cargar_contenido_c4

    def contar(*args):
        cargas.append(1)
        return cargar(*args)

    monkeypatch.setattr(motor_real, "cargar_contenido_c4", contar)
    with caplog.at_level(logging.WARNING, logger="app.api"):
        assert motor_real.obtener_snapshot() is None
        assert motor_real.obtener_snapshot() is None
    assert len(cargas) == 1
    assert _avisos(caplog).count("motivo=C4_INVALIDO") == 1

    preguntas.write_bytes(original)  # corregido, sin tocar el manifest
    st = preguntas.stat()
    os.utime(preguntas, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    assert motor_real.obtener_snapshot() is not None
    assert len(cargas) == 2
