"""Tests de resiliencia a datos mal ingresados (sanitizer, opción A).

Verifican que la caracterización NO se rompe ni engaña con datos sucios:
normaliza lo recuperable, marca lo dudoso, nunca inventa. Sin DB.
"""
from __future__ import annotations

from app.context.sanitizer import (
    Calidad, ReporteCalidad,
    sanear_edad, sanear_fecha_nacimiento, sanear_ingreso, sanear_parentesco,
    sanear_severidad_discapacidad, sanear_sexo, sanear_tramo_rsh,
)


# --- fecha / edad ------------------------------------------------------------

def test_fecha_iso_valida_es_ok():
    s = sanear_fecha_nacimiento("2015-01-01")
    assert s.calidad is Calidad.OK and s.valor == "2015-01-01"


def test_fecha_con_slash_se_normaliza():
    s = sanear_fecha_nacimiento("2015/01/01")
    assert s.calidad is Calidad.NORMALIZADO and s.valor == "2015-01-01"


def test_fecha_dd_mm_yyyy_se_normaliza():
    s = sanear_fecha_nacimiento("01-02-2015")
    assert s.calidad is Calidad.NORMALIZADO and s.valor == "2015-02-01"


def test_fecha_inexistente_es_ilegible():
    s = sanear_fecha_nacimiento("2015-13-99")
    assert s.calidad is Calidad.ILEGIBLE and s.valor is None


def test_fecha_basura_es_ilegible_no_rompe():
    s = sanear_fecha_nacimiento("ayer")
    assert s.calidad is Calidad.ILEGIBLE and s.valor is None


def test_edad_derivada_ok():
    s = sanear_edad("2015-01-01", "2026-10-13")
    assert s.valor == 11 and s.utilizable


def test_edad_fuera_de_rango_es_sospechosa():
    s = sanear_edad("1850-01-01", "2026-10-13")
    assert s.calidad is Calidad.SOSPECHOSO and s.valor and s.valor > 120


# --- parentesco --------------------------------------------------------------

def test_parentesco_valido_ok():
    assert sanear_parentesco("HIJO_HIJA").calidad is Calidad.OK


def test_parentesco_mal_escrito_se_normaliza():
    s = sanear_parentesco("hijo")
    assert s.calidad is Calidad.NORMALIZADO and s.valor == "HIJO_HIJA"


def test_parentesco_conyuge_mapea_pareja():
    assert sanear_parentesco("cónyuge").valor == "PAREJA"


def test_parentesco_desconocido_es_ilegible():
    s = sanear_parentesco("primo-segundo-politico")
    assert s.calidad is Calidad.ILEGIBLE and s.valor is None


# --- sexo --------------------------------------------------------------------

def test_sexo_normaliza_femenino():
    s = sanear_sexo("Femenino")
    assert s.calidad is Calidad.NORMALIZADO and s.valor == "F"


def test_sexo_f_es_ok():
    assert sanear_sexo("F").calidad is Calidad.OK


def test_sexo_basura_ilegible():
    assert sanear_sexo("otro").calidad is Calidad.ILEGIBLE


# --- tramo RSH ---------------------------------------------------------------

def test_tramo_valido_ok():
    assert sanear_tramo_rsh("40").calidad is Calidad.OK


def test_tramo_con_espacios_es_utilizable():
    s = sanear_tramo_rsh(" 40 ")
    assert s.valor == 40 and s.utilizable


def test_tramo_fuera_de_escala_es_sospechoso():
    s = sanear_tramo_rsh("45")
    assert s.calidad is Calidad.SOSPECHOSO and s.valor == 45


def test_tramo_no_numerico_ilegible():
    assert sanear_tramo_rsh("cuarenta").calidad is Calidad.ILEGIBLE


# --- ingreso -----------------------------------------------------------------

def test_ingreso_entero_ok():
    s = sanear_ingreso(300000)
    assert s.calidad is Calidad.OK and s.valor == 300000


def test_ingreso_con_separador_miles_se_normaliza():
    s = sanear_ingreso("300.000")
    assert s.calidad is Calidad.NORMALIZADO and s.valor == 300000


def test_ingreso_con_signo_peso_se_normaliza():
    s = sanear_ingreso("$ 300.000")
    assert s.valor == 300000 and s.utilizable


def test_ingreso_basura_ilegible():
    s = sanear_ingreso("mucho")
    assert s.calidad is Calidad.ILEGIBLE and s.valor is None


def test_ingreso_negativo_sospechoso():
    s = sanear_ingreso("-5000")
    assert s.calidad is Calidad.SOSPECHOSO


# --- severidad discapacidad --------------------------------------------------

def test_severidad_grave_mapea_severa():
    s = sanear_severidad_discapacidad("grave")
    assert s.valor == "SEVERA" and s.calidad is Calidad.NORMALIZADO


# --- reporte -----------------------------------------------------------------

def test_reporte_acumula_inconsistencias_y_resumen():
    r = ReporteCalidad()
    r.registrar(sanear_tramo_rsh("40"))          # OK
    r.registrar(sanear_tramo_rsh("45"))          # SOSPECHOSO
    r.registrar(sanear_parentesco("hijo"))       # NORMALIZADO
    r.registrar(sanear_sexo("otro"))             # ILEGIBLE

    incon = r.inconsistencias()
    assert len(incon) == 3   # todo menos el OK
    resumen = r.resumen()
    assert resumen["OK"] == 1
    assert resumen["SOSPECHOSO"] == 1
    assert resumen["NORMALIZADO"] == 1
    assert resumen["ILEGIBLE"] == 1
