"""Filtro de contexto hacia el LLM (spec §2.7.3).

Un único lugar donde se decide qué del `contexto_familia` puede ver el modelo.
Usa **allowlist** (lista blanca): solo pasa lo explícitamente permitido; todo
lo demás se descarta. Esto es más seguro que una blocklist, porque un campo
nuevo no permitido no se filtra por error.

Qué recibe el LLM (§2.7.3):
    - composicion (roles y edades)
    - rsh.tramo
    - ingreso_per_capita_rango
    - formato_preferido
    - idioma_mensaje
    (+ la salida del motor y el catálogo, que se inyectan aparte)

Nunca:
    nombres, RUT, folio RSH, teléfono, nacionalidad, diagnósticos, datos de
    salud, derivaciones judiciales, señales de vulnerabilidad individuales.

El test `test_context_filter` falla si aparece cualquier campo prohibido.
"""
from __future__ import annotations

# Campos de primer nivel del contexto que SÍ puede ver el LLM.
CAMPOS_PERMITIDOS_LLM = {
    "composicion",
    "ingreso_per_capita_rango",
    "formato_preferido",
    "idioma_mensaje",
}

# De `rsh` solo se permite el tramo (no `tiene`, no folio, no estado).
RSH_PERMITIDO = {"tramo"}

# De cada item de `composicion` solo rol + edad (nunca id ni nombre).
COMPOSICION_PERMITIDO = {"rol", "edad"}

# Marcadores/claves que, de aparecer, indican una fuga de privacidad.
# Se usan en la verificación defensiva (y en el test).
CAMPOS_PROHIBIDOS = {
    "nombre", "nombres", "apellido", "rut", "folio", "folio_rsh",
    "folio_rsh_simulado", "telefono", "teléfono", "correo", "email",
    "nacionalidad", "diagnostico", "diagnóstico", "salud", "prevision_salud",
    "fonasa_tramo", "derivacion", "derivación", "sename", "tribunal",
    "senales_vulnerabilidad", "senales_urgencia", "puntaje_cse",
    "jefa_hogar_sernameg", "identificador_mod11_simulado",
    "inconsistencias", "no_informado", "id_familia",
}


def filtrar_para_llm(contexto: dict) -> dict:
    """Devuelve una copia del contexto SOLO con los campos permitidos (§2.7.3).

    No muta la entrada. Cualquier campo no listado en la allowlist se descarta.
    """
    salida: dict = {}

    for clave in CAMPOS_PERMITIDOS_LLM:
        if clave not in contexto:
            continue
        if clave == "composicion":
            salida["composicion"] = [
                {k: v for k, v in item.items() if k in COMPOSICION_PERMITIDO}
                for item in contexto["composicion"]
            ]
        else:
            salida[clave] = contexto[clave]

    # rsh: solo el tramo.
    rsh = contexto.get("rsh")
    if isinstance(rsh, dict) and "tramo" in rsh:
        salida["rsh"] = {"tramo": rsh["tramo"]}

    return salida


def contiene_campo_prohibido(obj) -> list[str]:
    """Busca recursivamente claves prohibidas en un objeto JSON-like.

    Devuelve la lista de claves prohibidas encontradas (vacía = limpio).
    Útil para la verificación defensiva y el test del filtro.
    """
    encontrados: list[str] = []

    def _walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in CAMPOS_PROHIBIDOS:
                    encontrados.append(str(k))
                _walk(v)
        elif isinstance(o, (list, tuple)):
            for item in o:
                _walk(item)

    _walk(obj)
    return encontrados
