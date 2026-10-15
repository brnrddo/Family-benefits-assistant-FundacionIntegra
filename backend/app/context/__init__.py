"""Ventana de contexto de la familia (M3b · Rol 1, spec §2.7).

Tres piezas:

- ``ficha_sintetica``  : ficha por familia derivada del dataset E-3. Los campos
  que no se pueden derivar quedan como ``NO_INFORMADO`` (nunca se inventan).
- ``contexto_familia`` : objeto C2 exacto (§2.7.2) que consume Rol 2, con
  ``inconsistencias`` y ``no_informado``.
- ``context_filter``   : deja pasar al LLM solo los campos permitidos (§2.7.3);
  un único lugar donde vive el filtro de privacidad.
"""

from .contexto_familia import construir_contexto, ContextoBuilder  # noqa: F401
from .context_filter import filtrar_para_llm, CAMPOS_PERMITIDOS_LLM  # noqa: F401
from .contrato_c2 import a_contrato_c2  # noqa: F401
from .ficha_sintetica import construir_ficha, NO_INFORMADO  # noqa: F401
