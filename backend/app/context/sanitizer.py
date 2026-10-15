"""Saneamiento y caracterización resiliente de datos (opción A).

Objetivo: que la caracterización de una persona/familia **no se rompa ni
engañe** cuando el dato viene mal ingresado o escrito. En vez de tragarse la
basura silenciosamente (devolver None y seguir), este módulo:

  1. **Normaliza** lo recuperable sin ambigüedad:
     "300.000" / "$300.000" -> 300000 ; " 40 " -> 40 ;
     "hijo_hija" -> "HIJO_HIJA" ; "Femenino" -> "F".
  2. **Valida** contra dominios conocidos (tramo RSH, parentesco, sexo, rangos).
  3. **Clasifica** cada dato: OK / NORMALIZADO / SOSPECHOSO / ILEGIBLE / AUSENTE.
  4. **Registra** en una lista de inconsistencias qué no cuadró y qué se hizo,
     para que la tía pregunte y Rol 2 lo muestre (spec §2.4.4: lo que no se
     sabe se convierte en pregunta).

Principio: **corregir lo inequívoco, marcar lo dudoso, nunca inventar.** Un dato
ilegible degrada a valor ausente PERO deja rastro; jamás se adivina.

Alcance (opción A): los campos que caracterizan a la persona y mueven la
elegibilidad: fecha de nacimiento/edad, parentesco, sexo registral, tramo RSH,
ingreso del hogar, severidad de discapacidad.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from enum import Enum


class Calidad(str, Enum):
    OK = "OK"                   # válido tal cual
    NORMALIZADO = "NORMALIZADO" # venía raro pero se arregló sin ambigüedad
    SOSPECHOSO = "SOSPECHOSO"   # interpretable pero fuera de rango esperado
    ILEGIBLE = "ILEGIBLE"       # no se pudo interpretar -> se trata como ausente
    AUSENTE = "AUSENTE"         # no venía dato


@dataclass
class Saneado:
    """Resultado de sanear un campo: valor final + cómo se obtuvo."""
    campo: str
    valor: object               # valor normalizado (o None si ILEGIBLE/AUSENTE)
    calidad: Calidad
    original: object = None      # lo que vino crudo (para la traza)
    nota: str | None = None      # explicación legible de qué pasó

    @property
    def utilizable(self) -> bool:
        return self.calidad in (Calidad.OK, Calidad.NORMALIZADO, Calidad.SOSPECHOSO)


# --- dominios válidos --------------------------------------------------------
TRAMOS_RSH_VALIDOS = {40, 50, 60, 70, 80, 90, 100}
PARENTESCOS_VALIDOS = {
    "PERSONA_REFERENCIA", "PAREJA", "HIJO_HIJA", "OTRO_PARIENTE",
}
SEXOS_VALIDOS = {"F", "M"}
SEVERIDADES_VALIDAS = {"LEVE", "MODERADA", "SEVERA"}

EDAD_MIN, EDAD_MAX = 0, 120
INGRESO_MIN, INGRESO_MAX = 0, 20_000_000   # pesos; fuera de esto = sospechoso

# sinónimos frecuentes de parentesco mal escrito
_PARENTESCO_ALIAS = {
    "HIJO": "HIJO_HIJA", "HIJA": "HIJO_HIJA", "HIJO/A": "HIJO_HIJA",
    "HIJOHIJA": "HIJO_HIJA",
    "REFERENCIA": "PERSONA_REFERENCIA", "JEFE_HOGAR": "PERSONA_REFERENCIA",
    "JEFA_HOGAR": "PERSONA_REFERENCIA", "TITULAR": "PERSONA_REFERENCIA",
    "CONYUGE": "PAREJA", "CÓNYUGE": "PAREJA", "ESPOSO": "PAREJA",
    "ESPOSA": "PAREJA", "CONVIVIENTE": "PAREJA",
    "ABUELO": "OTRO_PARIENTE", "ABUELA": "OTRO_PARIENTE", "TIO": "OTRO_PARIENTE",
    "TIA": "OTRO_PARIENTE", "OTRO": "OTRO_PARIENTE",
}
_SEXO_ALIAS = {
    "F": "F", "M": "M",
    "FEMENINO": "F", "MASCULINO": "M", "MUJER": "F", "HOMBRE": "M",
    "FEM": "F", "MASC": "M",
}


def _norm_txt(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


# --- saneadores por campo ----------------------------------------------------

def sanear_fecha_nacimiento(valor) -> Saneado:
    """Normaliza una fecha a ISO ``YYYY-MM-DD`` y valida que exista."""
    campo = "fecha_nacimiento"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    # tolera separadores / . y espacios
    s2 = re.sub(r"[./]", "-", s).replace(" ", "")
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s2)
    # también acepta DD-MM-YYYY
    if not m:
        m2 = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", s2)
        if m2:
            d, mo, y = m2.groups()
            s2 = f"{y}-{int(mo):02d}-{int(d):02d}"
            m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s2)
    if not m:
        return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                       f"fecha no interpretable: {valor!r}")
    y, mo, d = (int(x) for x in m.groups())
    try:
        iso = dt.date(y, mo, d).isoformat()
    except ValueError:
        return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                       f"fecha inexistente: {valor!r}")
    calidad = Calidad.OK if iso == s else Calidad.NORMALIZADO
    nota = None if calidad is Calidad.OK else f"normalizada desde {valor!r}"
    return Saneado(campo, iso, calidad, valor, nota)


def sanear_edad(valor_fecha, fecha_eval: str) -> Saneado:
    """Deriva edad en años desde la fecha de nacimiento saneada."""
    base = sanear_fecha_nacimiento(valor_fecha)
    if not base.utilizable:
        return Saneado("edad", None, base.calidad, valor_fecha, base.nota)
    y, mo, d = (int(x) for x in base.valor.split("-"))
    fy, fm, fd = (int(x) for x in fecha_eval.split("-"))
    edad = fy - y - ((fm, fd) < (mo, d))
    if edad < EDAD_MIN or edad > EDAD_MAX:
        return Saneado("edad", edad, Calidad.SOSPECHOSO, valor_fecha,
                       f"edad fuera de rango plausible: {edad}")
    cal = base.calidad if base.calidad is not Calidad.OK else Calidad.OK
    return Saneado("edad", edad, cal, valor_fecha, base.nota)


def sanear_parentesco(valor) -> Saneado:
    campo = "parentesco"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    up = s.upper().replace("-", "_").replace(" ", "_")
    if up in PARENTESCOS_VALIDOS:
        return Saneado(campo, up, Calidad.OK, valor)
    if up in _PARENTESCO_ALIAS:
        norm = _PARENTESCO_ALIAS[up]
        return Saneado(campo, norm, Calidad.NORMALIZADO, valor,
                       f"'{valor}' interpretado como {norm}")
    return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                   f"parentesco desconocido: {valor!r}")


def sanear_sexo(valor) -> Saneado:
    campo = "sexo_registral"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    up = s.upper()
    if up in _SEXO_ALIAS:
        norm = _SEXO_ALIAS[up]
        cal = Calidad.OK if up == norm else Calidad.NORMALIZADO
        nota = None if cal is Calidad.OK else f"'{valor}' interpretado como {norm}"
        return Saneado(campo, norm, cal, valor, nota)
    return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                   f"sexo no interpretable: {valor!r}")


def sanear_tramo_rsh(valor) -> Saneado:
    campo = "tramo_rsh"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    # quita todo lo no-dígito (espacios, %, etc.)
    digits = re.sub(r"[^\d]", "", s)
    if digits == "":
        return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                       f"tramo no numérico: {valor!r}")
    n = int(digits)
    if n in TRAMOS_RSH_VALIDOS:
        cal = Calidad.OK if s == str(n) else Calidad.NORMALIZADO
        nota = None if cal is Calidad.OK else f"normalizado desde {valor!r}"
        return Saneado(campo, n, cal, valor, nota)
    return Saneado(campo, n, Calidad.SOSPECHOSO, valor,
                   f"tramo {n} fuera de la escala {sorted(TRAMOS_RSH_VALIDOS)}")


def sanear_ingreso(valor) -> Saneado:
    """Normaliza montos: quita $, separador de miles, espacios."""
    campo = "ingreso_hogar"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    # ya numérico
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        n = float(valor)
    else:
        limpio = s.replace("$", "").replace(" ", "")
        # formato chileno: punto = miles, coma = decimal
        if "," in limpio and "." in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        elif "." in limpio and re.search(r"\.\d{3}(\D|$)", "." + limpio):
            # puntos como separador de miles (300.000)
            limpio = limpio.replace(".", "")
        elif "," in limpio:
            limpio = limpio.replace(",", ".")
        try:
            n = float(limpio)
        except ValueError:
            return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                           f"ingreso no numérico: {valor!r}")
    normalizado = int(round(n))
    cambio = str(valor).strip() != str(normalizado)
    if normalizado < INGRESO_MIN or normalizado > INGRESO_MAX:
        return Saneado(campo, normalizado, Calidad.SOSPECHOSO, valor,
                       f"ingreso fuera de rango plausible: {normalizado}")
    cal = Calidad.NORMALIZADO if cambio else Calidad.OK
    nota = f"normalizado desde {valor!r}" if cambio else None
    return Saneado(campo, normalizado, cal, valor, nota)


def sanear_severidad_discapacidad(valor) -> Saneado:
    campo = "discapacidad_severidad"
    s = _norm_txt(valor)
    if s is None:
        return Saneado(campo, None, Calidad.AUSENTE, valor)
    up = s.upper()
    if up in SEVERIDADES_VALIDAS:
        return Saneado(campo, up, Calidad.OK, valor)
    alias = {"GRAVE": "SEVERA", "ALTA": "SEVERA", "MEDIA": "MODERADA",
             "BAJA": "LEVE"}
    if up in alias:
        return Saneado(campo, alias[up], Calidad.NORMALIZADO, valor,
                       f"'{valor}' interpretado como {alias[up]}")
    return Saneado(campo, None, Calidad.ILEGIBLE, valor,
                   f"severidad desconocida: {valor!r}")


# --- recolector de inconsistencias ------------------------------------------
@dataclass
class ReporteCalidad:
    """Acumula los saneos de una familia para poblar `inconsistencias`."""
    saneos: list[Saneado] = field(default_factory=list)

    def registrar(self, s: Saneado) -> Saneado:
        self.saneos.append(s)
        return s

    def inconsistencias(self) -> list[str]:
        """Mensajes legibles de lo que NO estaba limpio (para la tía/Rol 2).

        Siempre se antepone el nombre del campo, para que el mensaje sea
        rastreable (p. ej. "parentesco: 'hijo' interpretado como HIJO_HIJA").
        """
        msgs: list[str] = []
        for s in self.saneos:
            if s.calidad in (Calidad.NORMALIZADO, Calidad.SOSPECHOSO, Calidad.ILEGIBLE):
                detalle = s.nota or s.calidad.value
                msgs.append(f"{s.campo}: {detalle}")
        return msgs

    def resumen(self) -> dict[str, int]:
        """Conteo por calidad (para KPIs de calidad de datos)."""
        out = {c.value: 0 for c in Calidad}
        for s in self.saneos:
            out[s.calidad.value] += 1
        return out
