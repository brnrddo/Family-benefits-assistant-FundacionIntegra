"""KPI real (B3, DEC-080): ``KpiResult`` de C3 desde el snapshot del motor y el
registro de conversaciones del proceso.

- Población: familias del snapshot en el alcance (``nacional``, ``jardin``,
  ``comuna`` o ``region``, por los ``JardinSummary`` del snapshot).
- Informadas: familias distintas con al menos una conversación (cualquier
  ``origin``) en el período; varias conversaciones de una familia cuentan una vez.
- Período: con ``desde``/``hasta`` se filtra por la fecha UTC de ``occurred_at``;
  sin ellos entran todas las conversaciones del proceso.
- Nuevas: el snapshot no marca familias nuevas, así que el conteo es 0 y el
  porcentaje ``null`` (divisor cero).
- Cobertura: % de las oportunidades de las familias informadas mencionadas en
  alguna de sus conversaciones.
- Brechas: por beneficio, familias con la oportunidad sin asignar ni en curso y
  no mencionada en una conversación (máx. 5; monto ``null`` si no hay ninguno).
- Supresión (``kpi.min_cell_size`` del C4, DEC-044): con menos familias que el
  umbral, ``suppressed`` y conteos en 0/``null``; una brecha bajo el umbral no se
  emite.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.api.errors import ApiError
from app.api.motor_real import MotorSnapshot
from app.priority import content_c4
from app.priority.content_c4 import cargar_contenido_c4

_MAX_GAPS = 5  # KpiResult.top_gaps.maxItems
_SIN_BRECHA = frozenset({"ASIGNADO", "GESTION_EN_CURSO"})
_CAMPO_ALCANCE = {"comuna": "commune_id", "region": "region_id"}


@lru_cache(maxsize=4)
def _min_cell_size(manifest: str, bundle_hash: str) -> int:
    """Umbral del mismo bundle con que se armó el snapshot (clave: su hash)."""
    return int(cargar_contenido_c4(Path(manifest)).ranking.kpi["min_cell_size"])


def _fecha(valor: str | None) -> date | None:
    if valor is None:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ApiError(status_code=422) from None


def _fecha_utc(occurred_at: str) -> date | None:
    try:
        dt = datetime.fromisoformat(occurred_at)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date()


def _pct(parte: int, total: int) -> float | None:
    return round(100 * parte / total, 1) if total else None


def _familias_alcance(snap: MotorSnapshot, nivel: str, scope_id: str | None) -> list[str]:
    if nivel == "nacional":
        return sorted(snap.familias)
    if scope_id is None:
        raise ApiError(status_code=422)
    if nivel == "jardin":
        gids = [scope_id] if scope_id in snap.jardines else []
    else:
        campo = _CAMPO_ALCANCE[nivel]
        gids = [g for g, j in snap.jardines.items() if j[campo] == scope_id]
    if not gids:
        raise ApiError(status_code=404)
    return sorted(f for g in gids for f in snap.familias_por_jardin[g])


def calcular(
    snap: MotorSnapshot,
    conversaciones: list[dict],
    nivel: str,
    scope_id: str | None,
    desde: str | None,
    hasta: str | None,
) -> dict:
    inicio, fin = _fecha(desde), _fecha(hasta)
    if inicio is not None and fin is not None and inicio > fin:
        raise ApiError(status_code=422)
    familias = _familias_alcance(snap, nivel, scope_id)
    en_alcance = set(familias)

    # family_id -> beneficios mencionados (una familia cuenta una sola vez).
    mencionados: dict[str, set[str]] = {}
    fechas: list[date] = []
    for c in conversaciones:
        if c["family_id"] not in en_alcance:
            continue
        dia = _fecha_utc(c["occurred_at"])
        if (inicio is not None or fin is not None) and (
            dia is None or (inicio is not None and dia < inicio) or (fin is not None and dia > fin)
        ):
            continue
        mencionados.setdefault(c["family_id"], set()).update(c["benefit_ids"])
        if dia is not None:
            fechas.append(dia)

    ahora = datetime.now(timezone.utc).replace(microsecond=0)
    hoy = ahora.date()
    marca = ahora.isoformat().replace("+00:00", "Z")
    total = len(familias)
    minimo = _min_cell_size(str(content_c4.CONTENT_MANIFEST), snap.content_bundle_hash)
    suprimido = total < minimo

    informadas = len(mencionados)
    opps_informadas = [
        (o["benefit_id"], f) for f in mencionados for o in snap.familias[f]["opportunities"]
    ]
    cubiertas = sum(1 for bid, f in opps_informadas if bid in mencionados[f])

    brechas: dict[str, list] = {}
    for f in familias:
        hablados = mencionados.get(f, set())
        for o in snap.familias[f]["opportunities"]:
            if o["access_state"] in _SIN_BRECHA or o["benefit_id"] in hablados:
                continue
            fila = brechas.setdefault(o["benefit_id"], [0, None])
            fila[0] += 1
            if o["estimated_annual_amount"] is not None:
                fila[1] = (fila[1] or 0.0) + o["estimated_annual_amount"]
    top_gaps = [
        {"benefit_id": bid, "family_count": n, "potential_annual_amount": monto}
        for bid, (n, monto) in sorted(brechas.items(), key=lambda kv: (-kv[1][0], kv[0]))
        if n >= minimo
    ][:_MAX_GAPS]

    return {
        "level": nivel,
        "scope_id": scope_id,
        "period_start": (inicio or min(fechas, default=fin or hoy)).isoformat(),
        "period_end": (fin or max([hoy, *fechas, *([inicio] if inicio else [])])).isoformat(),
        "total_families": total,
        "informed_families": 0 if suprimido else informadas,
        "informed_percentage": None if suprimido else _pct(informadas, total),
        "total_new_families": 0,
        "informed_new_families": 0,
        "informed_new_percentage": None,
        "opportunity_coverage_percentage": (
            None if suprimido else _pct(cubiertas, len(opps_informadas))
        ),
        "suppressed": suprimido,
        "top_gaps": [] if suprimido else top_gaps,
        "calculated_at": marca,
        "watermark": marca,
    }
