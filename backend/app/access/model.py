"""Tipos del estado de acceso y del checklist de requisitos (M3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EstadoAcceso(str, Enum):
    """Estado de acceso combinando elegibilidad + gestiones (spec §7)."""
    ASIGNADO = "ASIGNADO"                       # ya lo recibe (VIGENTE)
    GESTION_EN_CURSO = "GESTION_EN_CURSO"       # en trámite
    GESTION_RECHAZADA = "GESTION_RECHAZADA"     # se lo rechazaron pese a cumplir
    ELEGIBLE_SIN_ASIGNACION = "ELEGIBLE_SIN_ASIGNACION"  # LA BRECHA (SI confirmado, sin gestión)
    SIN_CUPO = "SIN_CUPO"                        # elegible pero sobre el cupo
    PENDIENTE_ANTECEDENTES = "PENDIENTE_ANTECEDENTES"    # SI preliminar (falta acreditar)
    INDETERMINADO = "INDETERMINADO"             # falta un dato -> preguntar
    NO_APLICA = "NO_APLICA"                     # no cumple criterios


# Semáforo para la UI (lenguaje de la tía).
SEMAFORO = {
    EstadoAcceso.ELEGIBLE_SIN_ASIGNACION: "verde",   # puede pedirlo ya
    EstadoAcceso.GESTION_RECHAZADA: "verde",
    EstadoAcceso.PENDIENTE_ANTECEDENTES: "amarillo", # preguntar/acreditar primero
    EstadoAcceso.INDETERMINADO: "amarillo",
    EstadoAcceso.SIN_CUPO: "amarillo",
    EstadoAcceso.ASIGNADO: "azul",                   # ya lo tiene
    EstadoAcceso.GESTION_EN_CURSO: "azul",
    EstadoAcceso.NO_APLICA: "gris",
}


@dataclass
class RequisitoDoc:
    """Un ítem del checklist: qué papel/dato se necesita."""
    campo: str
    documento: str
    cumplido: bool            # el criterio ya se verificó con dato observado
    faltante: bool            # el dato falta (hay que conseguirlo/preguntarlo)


@dataclass
class Checklist:
    """Qué necesita la familia para obtener/formalizar el beneficio."""
    modalidad_acceso: str | None
    requiere_accion_familia: bool
    canal: str | None               # dónde ir
    ventana_desde: str | None
    ventana_hasta: str | None
    fuente_url: str | None          # más información (oficial)
    documentos: list[RequisitoDoc] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "modalidad_acceso": self.modalidad_acceso,
            "requiere_accion_familia": self.requiere_accion_familia,
            "canal": self.canal,
            "ventana_desde": self.ventana_desde,
            "ventana_hasta": self.ventana_hasta,
            "fuente_url": self.fuente_url,
            "documentos": [
                {"campo": d.campo, "documento": d.documento,
                 "cumplido": d.cumplido, "faltante": d.faltante}
                for d in self.documentos
            ],
        }


@dataclass
class ResultadoAcceso:
    """Salida de M3 para un par (familia, beneficio)."""
    id_familia: str
    id_beneficio: str
    estado: EstadoAcceso
    semaforo: str
    preliminar: bool                      # sub-flag: el SI venía con supuesto
    tiene_gestion: bool
    ultimo_estado_gestion: str | None
    id_postulacion: str | None
    checklist: Checklist | None
    # Se arrastra el resultado de elegibilidad para la UI/traza.
    elegibilidad: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id_familia": self.id_familia,
            "id_beneficio": self.id_beneficio,
            "estado": self.estado.value,
            "semaforo": self.semaforo,
            "preliminar": self.preliminar,
            "tiene_gestion": self.tiene_gestion,
            "ultimo_estado_gestion": self.ultimo_estado_gestion,
            "id_postulacion": self.id_postulacion,
            "checklist": self.checklist.to_dict() if self.checklist else None,
            "elegibilidad": self.elegibilidad,
        }
