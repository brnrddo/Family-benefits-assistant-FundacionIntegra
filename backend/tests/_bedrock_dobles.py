"""Dobles de prueba de Bedrock (prefijo ``_``: pytest no recoge este archivo).

Mismo patrón que ``tests/test_genai_bedrock.py`` (que no se toca): el cliente
``bedrock-runtime`` se inyecta y el reloj del provider se sustituye, así la
suite corre sin red, sin credenciales, sin boto3 y sin dormir de verdad.
"""
from __future__ import annotations


class _RelojFalso:
    """Reemplaza al módulo ``time`` dentro del provider: no duerme de verdad."""

    def __init__(self, inicio: float = 0.0):
        self.t = inicio
        self.esperas: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.t += segundos


class ClienteFalso:
    """Doble del cliente ``bedrock-runtime``; registra las llamadas recibidas."""

    def __init__(self, *, acciones_guardrail=None, respuesta_converse=None,
                 error_converse: Exception | None = None):
        # Una acción por llamada a apply_guardrail, en orden (INPUT, OUTPUT).
        self.acciones_guardrail = list(acciones_guardrail or ["NONE", "NONE"])
        self.respuesta_converse = respuesta_converse
        self.error_converse = error_converse
        self.llamadas: list[tuple[str, dict]] = []

    @property
    def operaciones(self) -> list[str]:
        return [op for op, _ in self.llamadas]

    def apply_guardrail(self, **kwargs) -> dict:
        self.llamadas.append(("apply_guardrail", kwargs))
        accion = self.acciones_guardrail.pop(0) if self.acciones_guardrail else "NONE"
        return {"action": accion, "outputs": [], "assessments": []}

    def converse(self, **kwargs) -> dict:
        self.llamadas.append(("converse", kwargs))
        if self.error_converse is not None:
            raise self.error_converse
        return self.respuesta_converse


def respuesta_tooluse(datos: dict, stop_reason: str = "tool_use") -> dict:
    """Respuesta Converse con salida estructurada (``toolUse``)."""
    return {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "tu-1", "name": "responder", "input": datos}},
        ]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 150, "outputTokens": 60, "totalTokens": 210},
    }
