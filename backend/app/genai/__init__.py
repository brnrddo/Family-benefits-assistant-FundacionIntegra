"""Capa de IA generativa — base para el Rol 2 (spec §4, §9).

Rol 1 deja aquí **los contratos y un proveedor stub**, no la implementación
real contra AWS. El Rol 2 toma esta base y:
  1. rellena `BedrockProvider` (Amazon Bedrock · Claude vía Converse API),
  2. conecta los prompts de `content/prompts/*.md` (dueño: Rol 4),
  3. añade caché por (familia, beneficio, versión).

Principio no negociable (spec §2.4.1): el LLM **nunca decide elegibilidad**.
Caracteriza, normaliza y redacta a partir de lo que entregan el motor (M2),
el acceso (M3) y el contexto filtrado (M3b). Las salidas que el LLM "propone"
entran como hechos DECLARADO (no acreditado) → PRELIMINAR, nunca CONFIRMADO.

Privacidad: lo único que puede viajar al modelo es lo que deja pasar
`app/context/context_filter.filtrar_para_llm` (§2.7.3).
"""

from .llm_context import (PiiLeakError,  # noqa: F401
                          construir_llm_context)
from .provider import (BedrockError, BedrockProvider,  # noqa: F401
                       GuardrailIntervino, GuardrailNoConfigurado,
                       LLMProvider, LLMResponse, StubProvider, get_provider)
from .template_provider import (DISCLAIMER,  # noqa: F401
                                CatalogEntry, SourceCitation, TemplateError,
                                TemplateProvider, catalogo_desde_benefits,
                                es_pregunta_individual)
