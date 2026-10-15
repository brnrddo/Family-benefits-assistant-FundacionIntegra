"""Tipos y constantes del motor de elegibilidad (M2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tri(str, Enum):
    """Lógica de tres valores para resultados atómicos y agregados."""
    SI = "SI"
    NO = "NO"
    INDETERMINADO = "INDETERMINADO"


class Nivel(str, Enum):
    """Nivel de confianza; solo aplica cuando el resultado es SI."""
    CONFIRMADO = "CONFIRMADO"
    PRELIMINAR = "PRELIMINAR"


# Códigos de motivo (sugeridos por la especificación §6.4).
MOTIVO_CRITERIOS_CUMPLEN = "CRITERIOS_CUMPLEN"
MOTIVO_CRITERIO_NO_CUMPLE = "CRITERIO_NO_CUMPLE"
MOTIVO_DATO_FALTANTE = "DATO_FALTANTE"            # se concatena :<campo>
MOTIVO_DATO_RSH_FALTANTE = "DATO_RSH_FALTANTE"
MOTIVO_EVIDENCIA_DECLARADA = "EVIDENCIA_DECLARADA"
MOTIVO_FUERA_DE_VIGENCIA = "NO_APLICA_SIN_VERSION"


@dataclass
class Hecho:
    """Un dato resuelto para una entidad (hogar o integrante) a una fecha.

    - ``valor`` ya viene normalizado al tipo apropiado (int/float/bool/str/date-str).
    - ``presente=False`` significa que el dato no existe en el dataset -> el motor
      lo tratará como INDETERMINADO (y lo convertirá en pregunta más adelante).
    """
    campo: str
    valor: object = None
    presente: bool = False
    acreditada: bool = True
    estado_dato: str = "OBSERVADO"
    id_origen: str | None = None   # id de la fila de sustento (para la traza)


@dataclass
class TrazaRegla:
    """Resultado de evaluar una regla atómica, para la traza explicable."""
    id_regla: str
    campo: str
    operador: str
    esperado: object
    observado: object
    resultado: Tri
    binding_grupo: str
    id_integrante_evaluado: str | None = None
    id_hecho: str | None = None
    nota: str | None = None


@dataclass
class ResultadoBeneficio:
    """Salida del motor para un par (familia, beneficio)."""
    id_familia: str
    id_beneficio: str
    id_version: str | None
    fecha_evaluacion: str
    resultado: Tri
    nivel: Nivel | None = None
    motivos: list[str] = field(default_factory=list)
    datos_faltantes: list[str] = field(default_factory=list)
    entidad_ganadora: dict[str, str] = field(default_factory=dict)
    monto_estimado: int | None = None
    traza: list[TrazaRegla] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id_familia": self.id_familia,
            "id_beneficio": self.id_beneficio,
            "id_version": self.id_version,
            "fecha_evaluacion": self.fecha_evaluacion,
            "resultado": self.resultado.value,
            "nivel": self.nivel.value if self.nivel else None,
            "motivos": self.motivos,
            "datos_faltantes": self.datos_faltantes,
            "entidad_ganadora": self.entidad_ganadora,
            "monto_estimado": self.monto_estimado,
            "traza": [
                {
                    "id_regla": t.id_regla,
                    "campo": t.campo,
                    "operador": t.operador,
                    "esperado": t.esperado,
                    "observado": t.observado,
                    "resultado": t.resultado.value,
                    "binding_grupo": t.binding_grupo,
                    "id_integrante_evaluado": t.id_integrante_evaluado,
                    "id_hecho": t.id_hecho,
                    "nota": t.nota,
                }
                for t in self.traza
            ],
        }
