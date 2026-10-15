"""Ejemplo de caracterización con LLM — PATRÓN para el Rol 2 (spec §9).

NO es la implementación final. Muestra el patrón correcto y seguro para que el
Rol 2 lo tome como base:

  1. Lo único que viaja al modelo es el contexto YA filtrado
     (`context_filter.filtrar_para_llm`, §2.7.3) + texto libre que la tía
     escribió. Nunca nombres, RUT, salud, etc.
  2. El LLM devuelve una propuesta ESTRUCTURADA (json_schema), no texto libre.
  3. Esa propuesta entra como hechos DECLARADO / no acreditada → el motor la
     tratará como PRELIMINAR, nunca CONFIRMADO (el LLM no decide elegibilidad).
  4. Con el StubProvider todo corre sin AWS (plan B §4).

Caso de uso típico (ficha digital S2): la tía escribe en lenguaje natural
("vive con la abuela postrada y dos niños chicos") y el LLM extrae una
caracterización estructurada que el motor puede usar como pistas DECLARADO.
"""
from __future__ import annotations

from .provider import LLMProvider, get_provider

# Schema de ejemplo de la caracterización que se le pide al modelo. El Rol 4
# afina el prompt; el Rol 2 puede ampliar el schema. Campos deliberadamente
# NO sensibles (roles/edades/señales), coherentes con el contrato C2.
SCHEMA_CARACTERIZACION = {
    "type": "object",
    "properties": {
        "integrantes_detectados": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rol": {"type": "string"},
                    "edad_aprox": {"type": "integer"},
                    "dependencia": {"type": "boolean"},
                },
            },
        },
        "senales_detectadas": {"type": "array", "items": {"type": "string"}},
        "confianza": {"type": "number"},
    },
    "required": ["integrantes_detectados"],
}

SYSTEM = (
    "Eres un asistente que SOLO estructura información ya entregada. "
    "No inventas datos ni decides si una familia califica a un beneficio. "
    "Si algo no está en el texto, no lo completes."
)


def caracterizar_texto_libre(
    texto_tia: str,
    contexto_filtrado: dict,
    provider: LLMProvider | None = None,
) -> dict:
    """Devuelve una caracterización estructurada (propuesta, no decisión).

    `contexto_filtrado` DEBE venir de `context_filter.filtrar_para_llm`. Esta
    función no vuelve a filtrar, pero tampoco añade datos sensibles al prompt.

    El resultado se marca como propuesta del LLM: quien lo consuma debe
    registrarlo como hecho DECLARADO/no acreditado (PRELIMINAR), nunca como
    verdad confirmada.
    """
    provider = provider or get_provider()
    prompt = (
        "Contexto no sensible de la familia (JSON):\n"
        f"{contexto_filtrado}\n\n"
        "Texto escrito por la educadora sobre la familia:\n"
        f"\"{texto_tia}\"\n\n"
        "Extrae SOLO lo que el texto dice, con el schema indicado."
    )
    resp = provider.generar(
        prompt, system=SYSTEM, json_schema=SCHEMA_CARACTERIZACION, temperatura=0.2)
    return {
        "propuesta": resp.datos or {},
        "origen": "LLM",
        "proveedor": resp.proveedor,
        "estado_dato": "DECLARADO",     # nunca OBSERVADO/acreditado
        "acreditada": False,            # => el motor dará PRELIMINAR como máximo
    }
