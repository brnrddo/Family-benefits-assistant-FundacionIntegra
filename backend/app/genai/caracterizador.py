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

**Límite de egreso (falla cerrado).** Este patrón SOLO corre contra el
proveedor local (`StubProvider`): el prompt mezcla texto libre sin tipar con un
contexto que viene de `context_filter.filtrar_para_llm` y NO de
`llm_context.construir_llm_context`, así que no está validado contra el schema
cerrado `LlmContextV1`. Mandarlo a un proveedor cloud dejaría a Guardrails como
única barrera y Guardrails no anonimiza (PRIVACIDAD_DEMO §"Barrera previa y
GenAI"). Habilitar un proveedor remoto aquí exige antes: (a) construir el
contexto con la allowlist positiva y (b) decidir la política de entrada del
texto libre (rechazar, tipar o sanear). Ambas son decisiones de producto, no se
resuelven cambiando `E3_LLM_PROVIDER`.
"""
from __future__ import annotations

from .llm_context import PiiLeakError
from .provider import LLMProvider, StubProvider, get_provider

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


def _exigir_proveedor_local(provider: LLMProvider) -> None:
    """Falla cerrado si el proveedor no es local: este prompt no puede salir.

    Guarda de egreso del patrón (ver el límite documentado en el módulo). No
    inspecciona ni "limpia" el contenido: cierra la vía completa, que es lo que
    exige la política ante duda ("cerrar la entrada o usar `TemplateProvider`").
    El mensaje lleva solo el nombre del proveedor, nunca el prompt ni el
    contexto.
    """
    if not isinstance(provider, StubProvider):
        raise PiiLeakError(
            "caracterizar_texto_libre solo admite el proveedor local "
            f"'{StubProvider.nombre}' (recibido: "
            f"{getattr(provider, 'nombre', type(provider).__name__)!r}): el "
            "prompt lleva texto libre sin tipar y un contexto que no pasó por "
            "construir_llm_context; enviarlo a un proveedor remoto saltaría la "
            "allowlist de LlmContextV1"
        )


def caracterizar_texto_libre(
    texto_tia: str,
    contexto_filtrado: dict,
    provider: LLMProvider | None = None,
) -> dict:
    """Devuelve una caracterización estructurada (propuesta, no decisión).

    `contexto_filtrado` DEBE venir de `context_filter.filtrar_para_llm`. Esta
    función no vuelve a filtrar, pero tampoco añade datos sensibles al prompt.

    Solo corre con el proveedor local: cualquier otro (p. ej. `BedrockProvider`
    vía `E3_LLM_PROVIDER=bedrock`, o uno inyectado) lanza `PiiLeakError` antes
    de armar el prompt y nada sale del proceso.

    El resultado se marca como propuesta del LLM: quien lo consuma debe
    registrarlo como hecho DECLARADO/no acreditado (PRELIMINAR), nunca como
    verdad confirmada.
    """
    provider = provider or get_provider()
    _exigir_proveedor_local(provider)  # antes de construir el prompt
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


def declarados_desde_propuesta(propuesta: dict) -> dict:
    """Convierte una propuesta estructurada en el dict ``declarados`` del motor.

    Puente entre la capa GenAI (o la ficha digital de la tía) y la reevaluación
    (`engine.service.reevaluar_con_declarados`). La propuesta debe traer una
    sección ``hechos_declarados`` con la forma del contrato del motor:

        {
            "hechos_declarados": {
                "hogar": {campo_dato: valor, ...},
                "integrante": {id_integrante: {campo_dato: valor, ...}, ...},
            }
        }

    Solo se dejan pasar campos declarables conocidos
    (`engine.facts.CAMPOS_DECLARABLES`); el valor se valida/convierte y, si es
    ilegible, se descarta. Las claves desconocidas se ignoran (no se inventan
    campos ni se decide elegibilidad aquí). Devuelve ``{}`` si no hay nada
    utilizable.
    """
    from ..engine.facts import CAMPOS_DECLARABLES, _coerce_declarado

    fuente = (propuesta or {}).get("hechos_declarados", {}) or {}
    salida: dict = {}

    hogar = {}
    for campo, valor in (fuente.get("hogar") or {}).items():
        if campo in CAMPOS_DECLARABLES and _coerce_declarado(campo, valor) is not None:
            hogar[campo] = valor
    if hogar:
        salida["hogar"] = hogar

    integrantes: dict = {}
    for pid, campos in (fuente.get("integrante") or {}).items():
        limpio = {
            c: v for c, v in (campos or {}).items()
            if c in CAMPOS_DECLARABLES and _coerce_declarado(c, v) is not None
        }
        if limpio:
            integrantes[pid] = limpio
    if integrantes:
        salida["integrante"] = integrantes

    return salida
