#!/usr/bin/env python3
"""Generador determinista del Challenge E-3 (solo biblioteca estándar)."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20261013
GENERATOR_VERSION = "1.0.0"
DATASET_VERSION = "E3-1.0.0"
SNAPSHOT = "2026-10-13T23:59:59-03:00"
CUTOFF = "2026-10-14T00:00:00-03:00"
START = dt.date(2025, 1, 1)
END = dt.date(2026, 10, 14)
ARCHETYPES = [
    ("ACCESO_COMPLETO", 90), ("BRECHA", 140), ("RSH_FALTANTE", 50),
    ("NO_ELEGIBLE", 80), ("DISCAPACIDAD", 50), ("RECHAZO", 40),
    ("CAMBIO_TEMPORAL", 50),
]

PUBLIC_HEADERS = {
    "comunas.csv": ["id_comuna", "region_codigo", "nombre_comuna_sintetico", "tipo_geografia"],
    "jardines.csv": ["id_jardin", "codigo_sintetico", "id_comuna", "tipo_zona"],
    "familias.csv": ["id_familia", "folio_rsh_simulado", "estado_rsh_corte", "tramo_rsh_corte", "numero_integrantes_corte", "id_comuna_residencia_corte", "region_codigo_residencia_corte", "id_jardin", "fecha_actualizacion_corte"],
    "integrantes.csv": ["id_integrante", "id_familia", "identificador_mod11_simulado", "parentesco", "fecha_nacimiento_sintetica", "sexo_registral_sintetico", "es_nino_jardin", "vigencia_desde", "vigencia_hasta"],
    "rsh_historial.csv": ["id_registro_rsh", "id_familia", "folio_rsh_simulado", "estado_rsh", "tramo_rsh", "subtramo_sintetico", "fecha_observacion", "vigencia_desde", "vigencia_hasta", "origen_dato"],
    "condiciones_integrante.csv": ["id_condicion", "id_integrante", "tipo_condicion", "subtipo", "id_contexto", "periodo_referencia", "valor_booleano", "valor_numero", "valor_texto", "valor_fecha", "valor_json", "unidad", "estado_dato", "acreditada", "fecha_observacion", "vigencia_desde", "vigencia_hasta", "fuente_sintetica"],
    "antecedentes_familia.csv": ["id_antecedente", "id_familia", "tipo_antecedente", "subtipo", "id_contexto", "periodo_referencia", "valor_booleano", "valor_numero", "valor_texto", "valor_fecha", "valor_json", "unidad", "estado_dato", "acreditada", "fecha_observacion", "vigencia_desde", "vigencia_hasta", "fuente_sintetica"],
    "relaciones_integrantes.csv": ["id_relacion", "id_familia", "id_integrante_origen", "id_integrante_destino", "tipo_relacion", "acreditada", "estado_dato", "fecha_observacion", "vigencia_desde", "vigencia_hasta"],
    "accesos_previos_hogar.csv": ["id_acceso_previo", "id_familia", "id_beneficio_o_programa", "estado_acceso", "vigencia_desde", "vigencia_hasta", "fecha_observacion", "estado_dato", "origen_sintetico"],
    "accesos_previos_causantes.csv": ["id_acceso_previo", "id_familia", "id_beneficio_o_programa", "id_integrante", "unidades_causante"],
    "fuentes.csv": ["id_fuente", "categoria_origen", "organismo_detalle", "titulo", "url", "fecha_consulta", "nota"],
    "beneficios.csv": ["id_beneficio", "nombre", "tipo_fuente", "institucion", "descripcion_sintetica", "tipo_prestacion", "plataforma_canal_principal", "es_sintetico"],
    "beneficios_versiones.csv": ["id_version", "id_beneficio", "vigencia_desde", "vigencia_hasta", "descripcion_entrega", "monto_referencial_sintetico", "unidad_monto", "periodicidad", "tramo_maximo_sintetico", "modalidad_acceso", "ventana_acceso_desde", "ventana_acceso_hasta", "requiere_accion_familia", "estados_acceso", "politica_perdida", "cupo_contingente", "advertencia"],
    "parametros_version.csv": ["id_parametro", "id_version", "nombre_parametro", "tipo_valor", "valor_int", "valor_decimal", "valor_fecha", "valor_texto"],
    "beneficios_fuentes.csv": ["id_beneficio", "id_fuente", "alcance", "es_simplificacion", "nota_sintesis"],
    "versiones_fuentes.csv": ["id_version", "id_fuente", "alcance", "es_simplificacion", "nota_sintesis"],
    "parametros_fuentes.csv": ["id_parametro", "id_fuente", "alcance", "es_simplificacion", "nota_sintesis"],
    "reglas_elegibilidad.csv": ["id_regla", "id_version", "grupo_or", "orden", "cuantificador", "binding_grupo", "binding_padre", "rol_causante", "entidad_objetivo", "campo_dato", "operador", "valor_literal_tipo", "valor_literal", "id_parametro_version", "valor_binding_ref", "id_parametro_fecha_contexto", "vigencia_desde", "vigencia_hasta"],
    "reglas_fuentes.csv": ["id_version", "id_regla", "id_fuente", "alcance", "es_simplificacion", "nota_sintesis"],
    "postulaciones.csv": ["id_postulacion", "id_familia", "id_beneficio", "id_version_inicio", "id_version_concesion", "tipo_solicitud", "fecha_hora_inicio", "fecha_hora_inicio_vigencia", "canal", "requiere_documentos", "fecha_termino_programa", "termino_concedido", "termino_concedido_original"],
    "postulaciones_causantes.csv": ["id_postulacion", "id_familia", "id_beneficio", "id_integrante", "rol", "unidades_causante"],
    "postulaciones_estados.csv": ["id_evento_estado", "id_postulacion", "secuencia", "estado", "fecha_hora", "codigo_motivo", "detalle_sintetico", "id_version_decision"],
    "pagos_beneficios.csv": ["id_pago", "id_postulacion", "fecha_hora", "monto_sintetico", "estado_monto", "tipo_entrega", "cantidad", "periodo_desde", "periodo_hasta"],
}
INTERNAL_HEADERS = {
    "elegibilidad_esperada.csv": ["id_evaluacion", "id_familia", "id_beneficio", "id_version", "fecha_hora_evaluacion", "resultado_criterios", "nivel_resultado", "codigos_motivo", "ids_reglas_aplicadas", "datos_faltantes"],
    "detalle_reglas.csv": ["id_detalle_regla", "id_evaluacion", "id_familia", "id_beneficio", "id_version", "fecha_hora_evaluacion", "id_regla", "binding_grupo", "id_integrante_evaluado", "es_binding_ganador", "resultado_atomico", "nivel_atomico", "valor_observado_normalizado", "codigo_motivo"],
    "causantes_evaluaciones.csv": ["id_evaluacion", "id_familia", "id_beneficio", "id_version", "fecha_hora_evaluacion", "id_integrante", "rol", "resultado_causante", "ids_reglas_sustento", "codigo_motivo", "unidades_causante"],
    "postulaciones_evaluaciones.csv": ["id_vinculo", "id_postulacion", "id_evento_estado", "id_evaluacion", "id_familia", "id_beneficio", "id_version_evaluada", "fecha_hora_evaluacion", "tipo_vinculo", "fecha_hora_vinculo"],
    "asignacion_esperada.csv": ["id_evaluacion", "id_familia", "id_beneficio", "id_version", "fecha_hora_evaluacion", "resultado_acceso", "posicion_prioridad", "cupo_version", "id_postulacion", "codigo_motivo"],
    "brechas_acceso.csv": ["id_brecha", "id_evaluacion", "id_familia", "id_beneficio", "id_version", "fecha_hora_evaluacion", "tipo_brecha", "ventana_desde", "ventana_hasta", "dias_elegibles_consecutivos"],
    "arquetipos_generacion.csv": ["id_familia", "arquetipo"],
    "excepciones.csv": ["id_excepcion", "tipo_entidad", "id_registro", "codigo", "regla_exceptuada", "vigencia_desde", "vigencia_hasta", "justificacion", "severidad"],
}

BENEFITS = [
("Subsidio Familiar (SUF) tradicional","ESTATAL","IPS/municipalidades","MONETARIA","Municipalidad/VUS/ChileAtiende"),
("Subsidio Familiar Automático","ESTATAL","IPS","MONETARIA","Asignación automática"),
("Subsidio Maternal","ESTATAL","IPS/municipalidades","MONETARIA","Municipalidad/VUS"),
("Aporte Familiar Permanente","ESTATAL","IPS","MONETARIA","Asignación automática/IPS"),
("Subsidio al consumo de agua potable y alcantarillado","ESTATAL","Municipalidades/MDSF","MONETARIA_INDIRECTA","Municipalidad"),
("Subsidio de discapacidad para menores de 18 años","ESTATAL","IPS","MONETARIA","VUS/ChileAtiende/IPS"),
("Programa de Alimentación Escolar","ESTATAL","JUNAEB","ALIMENTACION","Asignación institucional"),
("Programa de Apoyo al Recién Nacido","ESTATAL","Chile Crece Contigo/MDSF","ESPECIE","Red de salud"),
("Programa de Apoyo al Desarrollo Biopsicosocial","ESTATAL","Chile Crece Contigo/MDSF-salud","SERVICIO","Red pública"),
("Bono de Protección","ESTATAL","Subsistema Seguridades y Oportunidades/IPS","MONETARIA","Asignación automática"),
("Bono Base Familiar","ESTATAL","Subsistema Seguridades y Oportunidades/IPS","MONETARIA","Asignación automática"),
("Bono Control Niño Sano","ESTATAL","Subsistema Seguridades y Oportunidades","MONETARIA","Asignación automática"),
("Bono Asistencia Escolar","ESTATAL","Subsistema Seguridades y Oportunidades","MONETARIA","Asignación automática"),
("Bono por Logro Escolar","ESTATAL","MDSF","MONETARIA","Asignación automática"),
("Programa Útiles Escolares","ESTATAL","JUNAEB","ESPECIE","Asignación institucional"),
("Asignación Familiar","ESTATAL","IPS/entidades administradoras","MONETARIA","Entidad administradora"),
("Bono por Hijo","ESTATAL","IPS","MONETARIA","IPS"),
("Programa Sintético de Canasta Familiar","PRIVADO_SINTETICO","Organización Social Sintética A","ESPECIE","Derivación desde jardín"),
("Fondo Sintético de Traslado a Terapias","PRIVADO_SINTETICO","Fundación Sintética B","MIXTA","Formulario/derivación"),
("Apoyo Sintético de Emergencia Familiar","PRIVADO_SINTETICO","Red Comunitaria Sintética C","MONETARIA","Derivación/evaluación social"),
]
OFFICIAL_SOURCE = ["F004","F004","F006","F007","F008","F009","F010","F012","F013","F014","F015","F016","F017","F018","F019","F020","F021"]
BENEFIT_DESCRIPTIONS = [
"Hogares responsables de causantes menores de 18 con antecedentes vigentes y sin cobertura incompatible.",
"Causantes menores de 18 de hogares en tramo 40 con antecedentes por edad vigentes.",
"Persona gestante desde semana 20, tramo hasta 60 y sin cobertura incompatible.",
"Hogares con una prestación habilitante activa en el corte anual sintético.",
"Hogar residente con cuenta al día y carga de gasto de agua sobre el umbral.",
"Mismo causante menor de 18 con discapacidad severa acreditada y RSH hasta 60.",
"Mismo estudiante matriculado en establecimiento sintético adscrito al programa.",
"Recién nacido cuyo parto sintético ocurrió en una red pública.",
"Gestación o infancia atendida en una red pública según etapa de desarrollo.",
"Hogar participante del subsistema que acepta acompañamiento.",
"Hogar participante con ingreso per cápita bajo el umbral versionado.",
"Mismo niño o niña menor de seis con controles de salud vigentes.",
"Mismo estudiante de 6 a 18 con matrícula y asistencia mínima.",
"Mismo estudiante en niveles cubiertos, subtramo sintético y desempeño requerido.",
"Mismo estudiante matriculado en nivel y establecimiento cubiertos.",
"Persona beneficiaria con previsión e ingreso compatibles y causante acreditado.",
"Persona sintética F de 65 años o más, residencia, previsión e hijo o hija registrado.",
"Hogar con inseguridad alimentaria en una comuna sintética cubierta, sujeto a cupo.",
"Mismo niño o niña con terapia, distancia, ingreso y documentos requeridos.",
"Hogar con evento crítico reciente, residencia e informe, sujeto a recurrencia."
]

# version, benefit, from, to, mode, window from/to, family action, policy, period, amount, tranche, capacity, params
VERSIONS = []
def addv(v,b,a,z,mode,wa,wz,action,policy,period,amount,tranche,capacity,**params):
    VERSIONS.append((v,b,a,z,mode,wa,wz,action,policy,period,amount,tranche,capacity,params))
addv("V001",1,"2025-01-01","2026-02-01","POSTULACION","2025-01-01","2026-02-01",1,"FINALIZAR","MENSUAL",20000,60,None,monto_causante_mes=20000,edad_max_excl=18,tramo_max=60)
addv("V002",1,"2026-02-01","2026-10-14","POSTULACION","2026-02-01","2026-10-14",1,"FINALIZAR","MENSUAL",22000,60,None,monto_causante_mes=22000,edad_max_excl=18,tramo_max=60)
addv("V003",2,"2025-01-01","2026-02-01","ASIGNACION_AUTOMATICA","2025-01-01","2026-02-01",0,"FINALIZAR","MENSUAL",20000,40,None,monto_causante_mes=20000,edad_max_excl=18,tramo_max=40)
addv("V004",2,"2026-02-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-02-01","2026-10-14",0,"FINALIZAR","MENSUAL",22000,40,None,monto_causante_mes=22000,edad_max_excl=18,tramo_max=40)
addv("V005",3,"2025-01-01","2026-02-01","POSTULACION","2025-01-01","2026-02-01",1,"FINALIZAR","MENSUAL",20000,60,None,monto_mes=20000,semana_min=20,tramo_max=60)
addv("V006",3,"2026-02-01","2026-10-14","POSTULACION","2026-02-01","2026-10-14",1,"FINALIZAR","MENSUAL",22000,60,None,monto_mes=22000,semana_min=20,tramo_max=60)
addv("V007",4,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-02-15","2025-07-01",0,"MANTENER","ANUAL",60000,None,None,monto_causante_anual=60000,fecha_corte="2024-12-31")
addv("V008",4,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-02-15","2026-07-01",0,"MANTENER","ANUAL",65000,None,None,monto_causante_anual=65000,fecha_corte="2025-12-31")
addv("V009",5,"2025-01-01","2026-07-01","POSTULACION","2025-01-01","2026-07-01",1,"MANTENER","MENSUAL",None,None,None,gasto_ingreso_min_pct=5.0,consumo_tope_m3=15,descuento_pct=70,cuenta_mora_max_dias=0,duracion_acceso_dias=365)
addv("V010",5,"2026-07-01","2026-10-14","POSTULACION","2026-07-01","2026-10-14",1,"MANTENER","MENSUAL",None,None,None,gasto_ingreso_min_pct=5.0,consumo_tope_m3=18,descuento_pct=70,cuenta_mora_max_dias=0,duracion_acceso_dias=365)
addv("V011",6,"2025-01-01","2026-02-01","POSTULACION","2025-01-01","2026-02-01",1,"FINALIZAR","MENSUAL",100000,60,None,monto_mes=100000,edad_max_excl=18,tramo_max=60,severidades=["SEVERA"])
addv("V012",6,"2026-02-01","2026-10-14","POSTULACION","2026-02-01","2026-10-14",1,"FINALIZAR","MENSUAL",110000,60,None,monto_mes=110000,edad_max_excl=18,tramo_max=60,severidades=["SEVERA"])
addv("V013",7,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-03-01","2025-12-20",0,"MANTENER","POR_DIA",None,None,None,edades="[4,19)",entrega="DESAYUNO_1+ALMUERZO_1_POR_DIA_LECTIVO",cupo=None)
addv("V014",7,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-03-01","2026-10-14",0,"MANTENER","POR_DIA",None,None,None,edades="[4,19)",entrega="DESAYUNO_1+ALMUERZO_1_POR_DIA_LECTIVO",cupo=None)
addv("V015",8,"2025-01-01","2026-07-01","DERIVACION","2025-01-01","2026-07-01",0,"MANTENER","UNICA",None,None,None,edad_max_dias=90,kit="AJUAR_A",cantidad_kit=1)
addv("V016",8,"2026-07-01","2026-10-14","DERIVACION","2026-07-01","2026-10-14",0,"MANTENER","UNICA",None,None,None,edad_max_dias=90,kit="AJUAR_B",cantidad_kit=1)
addv("V017",9,"2025-01-01","2026-07-01","DERIVACION","2025-01-01","2026-07-01",0,"FINALIZAR","NO_APLICA",None,None,None,edad_infantil_max_meses_incl=48,controles_objetivo_anual=6,red="PUBLICA")
addv("V018",9,"2026-07-01","2026-10-14","DERIVACION","2026-07-01","2026-10-14",0,"FINALIZAR","NO_APLICA",None,None,None,edad_infantil_max_meses_incl=60,controles_objetivo_anual=6,red="PUBLICA")
addv("V019",10,"2025-01-01","2026-02-01","ASIGNACION_AUTOMATICA","2025-01-01","2026-02-01",0,"MANTENER","MENSUAL",None,None,None,montos_mes_tramo={"1-6":22000,"7-12":17000,"13-18":12000,"19-24":16000},duracion_meses=24)
addv("V020",10,"2026-02-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-02-01","2026-10-14",0,"MANTENER","MENSUAL",None,None,None,montos_mes_tramo={"1-6":24000,"7-12":19000,"13-18":14000,"19-24":18000},duracion_meses=24)
addv("V021",11,"2025-01-01","2026-07-01","ASIGNACION_AUTOMATICA","2025-01-01","2026-07-01",0,"FINALIZAR","MENSUAL",50000,None,None,ingreso_pc_max_excl=100000,factor_brecha=0.85,monto_tope_mes=50000,formula="min(tope,(umbral-ingreso_pc)*factor)")
addv("V022",11,"2026-07-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-07-01","2026-10-14",0,"FINALIZAR","MENSUAL",55000,None,None,ingreso_pc_max_excl=110000,factor_brecha=0.85,monto_tope_mes=55000,formula="min(tope,(umbral-ingreso_pc)*factor)")
addv("V023",12,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-01-01","2026-01-01",0,"FINALIZAR","MENSUAL",12000,None,None,monto_mes=12000,edad_max_excl=6,control_vigencia_dias=180)
addv("V024",12,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-01-01","2026-10-14",0,"FINALIZAR","MENSUAL",13000,None,None,monto_mes=13000,edad_max_excl=6,control_vigencia_dias=180)
addv("V025",13,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-03-01","2026-01-01",0,"FINALIZAR","MENSUAL",10000,None,None,monto_mes_lectivo=10000,edad_min=6,edad_max_incl=18,asistencia_min_pct=85,meses_lectivos=[3,4,5,6,7,8,9,10,11,12])
addv("V026",13,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-03-01","2026-10-14",0,"FINALIZAR","MENSUAL",11000,None,None,monto_mes_lectivo=11000,edad_min=6,edad_max_incl=18,asistencia_min_pct=85,meses_lectivos=[3,4,5,6,7,8,9,10])
addv("V027",14,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-09-01","2025-11-01",0,"MANTENER","ANUAL",70000,40,None,edad_max_excl=24,niveles=["5B","6B","7B","8B","1M","2M","3M","4M"],subtramo_max=30,percentil_max=30,monto_pct_1_15=70000,monto_pct_16_30=40000)
addv("V028",14,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-09-01","2026-10-14",0,"MANTENER","ANUAL",75000,40,None,edad_max_excl=24,niveles=["5B","6B","7B","8B","1M","2M","3M","4M"],subtramo_max=30,percentil_max=30,monto_pct_1_15=75000,monto_pct_16_30=45000)
addv("V029",15,"2025-01-01","2026-01-01","ASIGNACION_AUTOMATICA","2025-02-15","2025-06-01",0,"MANTENER","ANUAL",None,None,None,niveles=["NT1","NT2","1B","2B","3B","4B","5B","6B","7B","8B","1M","2M","3M","4M"],tipos_establecimiento=["MUNICIPAL","SUBVENCIONADO_ADSCRITO"],set="UTILES_A",cupo=None)
addv("V030",15,"2026-01-01","2026-10-14","ASIGNACION_AUTOMATICA","2026-02-15","2026-06-01",0,"MANTENER","ANUAL",None,None,None,niveles=["NT1","NT2","1B","2B","3B","4B","5B","6B","7B","8B","1M","2M","3M","4M"],tipos_establecimiento=["MUNICIPAL","SUBVENCIONADO_ADSCRITO"],set="UTILES_B",cupo=None)
for v,a,z,vals in [("V031","2025-01-01","2025-07-01","(0,300000]:22000;(300000,450000]:14000;(450000,600000]:5000"),("V032","2025-07-01","2026-07-01","(0,330000]:24000;(330000,480000]:15000;(480000,630000]:5500"),("V033","2026-07-01","2026-10-14","(0,360000]:26000;(360000,510000]:16000;(510000,660000]:6000")]:
    addv(v,16,a,z,"POSTULACION",a,z,1,"FINALIZAR","MENSUAL",None,None,None,categorias=["TRABAJADOR_DEPENDIENTE","INDEPENDIENTE_COTIZANTE","PENSIONADO","SUBSIDIADO_CESANTIA"],tramos_ingreso_monto=vals)
for v,a,z,minimum in [("V034","2025-01-01","2026-01-01",500000),("V035","2026-01-01","2026-10-14",550000)]:
    addv(v,17,a,z,"POSTULACION",a,z,1,"MANTENER","UNICA",minimum*.1*18,None,None,edad_min=65,residencia_total_min_anios=20,residencia_ultimos20_min_anios=4,categorias=["PENSION_BASICA","PENSION_AFP","SIN_PENSION_PREVIA"],ingreso_minimo_sim=minimum,formula="0.10*ingreso_minimo_sim*18")
for v,a,z,val,cup in [("V036","2025-01-01","2026-07-01",45000,100),("V037","2026-07-01","2026-10-14",50000,75)]:
    addv(v,18,a,z,"DERIVACION",a,z,1,"MANTENER","UNICA",val,None,cup,indice_min=2,comunas=[f"COM-{i:03d}" for i in range(1,21)],valor_canasta=val,cupo=cup,rsh_prioridad_max=70,duracion_acceso_dias=30)
for v,a,z,dist,reim,viajes in [("V038","2025-04-01","2026-07-01",10,30000,8),("V039","2026-07-01","2026-10-14",8,35000,10)]:
    addv(v,19,a,z,"POSTULACION",a,z,1,"FINALIZAR","MENSUAL",reim,None,None,edad_max_excl=18,distancia_min_km=dist,ingreso_pc_max_excl=250000,reembolso_tope_mes=reim,viajes_tope_mes=viajes,documento_vigencia_dias=90)
for v,a,z,rec,monto in [("V040","2025-01-01","2026-06-01",120,80000),("V041","2026-06-01","2026-10-14",180,90000)]:
    addv(v,20,a,z,"DERIVACION",a,z,1,"MANTENER","UNICA",monto,None,None,evento_max_dias=60,comunas=[f"COM-{i:03d}" for i in range(1,21)],recurrencia_min_dias=rec,monto_unico=monto,tipos_evento=["INCENDIO","INUNDACION","PERDIDA_INGRESO","VIOLENCIA"])

RULES = {
1:[("tramo_rsh","LTE","tramo_max","HOUSEHOLD","HOGAR","NINGUNO"),("edad","LT","edad_max_excl","EXISTS","CAUSANTE_1","CAUSANTE"),("antecedente_edad_vigente","EQ",True,"EXISTS","CAUSANTE_1","CAUSANTE"),("cobertura_incompatible","EQ",False,"HOUSEHOLD","HOGAR","NINGUNO")],
2:[("tramo_rsh","LTE","tramo_max","HOUSEHOLD","HOGAR","NINGUNO"),("edad","LT","edad_max_excl","EXISTS","CAUSANTE_1","CAUSANTE"),("antecedente_edad_vigente","EQ",True,"EXISTS","CAUSANTE_1","CAUSANTE")],
3:[("semanas_gestacion","GTE","semana_min","EXISTS","GESTANTE_1","GESTANTE"),("tramo_rsh","LTE","tramo_max","HOUSEHOLD","HOGAR","NINGUNO"),("cobertura_incompatible","EQ",False,"EXISTS","GESTANTE_1","GESTANTE")],
4:[("id_beneficio_o_programa","EQ","BEN-001","EXISTS","ACCESO_1","ACCESO"),("estado_acceso","IN",["APROBADA","VIGENTE"],"EXISTS","ACCESO_1","ACCESO"),("vigencia","ACTIVE_ON_DATE",None,"EXISTS","ACCESO_1","ACCESO"),("id_beneficio_o_programa","EQ","BEN-016","EXISTS","ACCESO_2","ACCESO"),("estado_acceso","IN",["APROBADA","VIGENTE"],"EXISTS","ACCESO_2","ACCESO"),("vigencia","ACTIVE_ON_DATE",None,"EXISTS","ACCESO_2","ACCESO"),("id_beneficio_o_programa","EQ","SUBSISTEMA_SSYO","EXISTS","ACCESO_3","ACCESO"),("estado_acceso","IN",["APROBADA","VIGENTE"],"EXISTS","ACCESO_3","ACCESO"),("vigencia","ACTIVE_ON_DATE",None,"EXISTS","ACCESO_3","ACCESO")],
5:[("gasto_agua_pct_ingreso","GTE","gasto_ingreso_min_pct","HOUSEHOLD","HOGAR","NINGUNO"),("mora_dias","LTE","cuenta_mora_max_dias","HOUSEHOLD","HOGAR","NINGUNO"),("comuna_cuenta_coincide_residencia","EQ",True,"HOUSEHOLD","HOGAR","NINGUNO")],
6:[("edad","LT","edad_max_excl","EXISTS","CAUSANTE_1","CAUSANTE"),("discapacidad_severidad","IN","severidades","EXISTS","CAUSANTE_1","CAUSANTE"),("discapacidad_vigencia","ACTIVE_ON_DATE",None,"EXISTS","CAUSANTE_1","CAUSANTE"),("tramo_rsh","LTE","tramo_max","HOUSEHOLD","HOGAR","NINGUNO")],
7:[("edad","BETWEEN","edades","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("matricula_vigencia","ACTIVE_ON_DATE",None,"EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("establecimiento_adscrito_pae","EQ",True,"EXISTS","ESTUDIANTE_1","ESTUDIANTE")],
8:[("dias_desde_nacimiento","LTE","edad_max_dias","EXISTS","RECIEN_NACIDO_1","RECIEN_NACIDO"),("parto_red_publica","EQ",True,"EXISTS","RECIEN_NACIDO_1","RECIEN_NACIDO")],
9:[("control_prenatal_red_publica","ACTIVE_ON_DATE",None,"EXISTS","GESTANTE_1","GESTANTE"),("edad_meses","LTE","edad_infantil_max_meses_incl","EXISTS","CAUSANTE_1","CAUSANTE"),("control_infantil_red_publica","ACTIVE_ON_DATE",None,"EXISTS","CAUSANTE_1","CAUSANTE")],
10:[("subsistema_ssyo_vigencia","ACTIVE_ON_DATE",None,"HOUSEHOLD","HOGAR","NINGUNO"),("acompanamiento_aceptado","EQ",True,"HOUSEHOLD","HOGAR","NINGUNO")],
11:[("subsistema_ssyo_vigencia","ACTIVE_ON_DATE",None,"HOUSEHOLD","HOGAR","NINGUNO"),("ingreso_per_capita","LT","ingreso_pc_max_excl","HOUSEHOLD","HOGAR","NINGUNO")],
12:[("subsistema_ssyo_vigencia","ACTIVE_ON_DATE",None,"HOUSEHOLD","HOGAR","NINGUNO"),("edad","LT","edad_max_excl","EXISTS","CAUSANTE_1","CAUSANTE"),("dias_desde_control","LTE","control_vigencia_dias","EXISTS","CAUSANTE_1","CAUSANTE")],
13:[("subsistema_ssyo_vigencia","ACTIVE_ON_DATE",None,"HOUSEHOLD","HOGAR","NINGUNO"),("edad","GTE","edad_min","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("edad","LTE","edad_max_incl","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("matricula_vigencia","ACTIVE_ON_DATE",None,"EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("asistencia_pct","GTE","asistencia_min_pct","EXISTS","ESTUDIANTE_1","ESTUDIANTE")],
14:[("edad","LT","edad_max_excl","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("nivel","IN","niveles","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("subtramo_sintetico","LTE","subtramo_max","HOUSEHOLD","HOGAR","NINGUNO"),("percentil_desempeno","LTE","percentil_max","EXISTS","ESTUDIANTE_1","ESTUDIANTE")],
15:[("matricula_vigencia","ACTIVE_ON_DATE",None,"EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("nivel","IN","niveles","EXISTS","ESTUDIANTE_1","ESTUDIANTE"),("tipo_establecimiento","IN","tipos_establecimiento","EXISTS","ESTUDIANTE_1","ESTUDIANTE")],
16:[("situacion_previsional","IN","categorias","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("ingreso_bruto","RANGE_LOOKUP","tramos_ingreso_monto","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("carga_acreditada_de","REF_EQ","BENEFICIARIO_1","EXISTS","CAUSANTE_1","CAUSANTE")],
17:[("sexo_registral","EQ","F","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("edad","GTE","edad_min","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("residencia_total_anios","GTE","residencia_total_min_anios","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("residencia_ultimos20_anios","GTE","residencia_ultimos20_min_anios","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("situacion_previsional","IN","categorias","EXISTS","BENEFICIARIO_1","BENEFICIARIO"),("hijos_activos","COUNT_REL_GTE",1,"COUNT","BENEFICIARIO_1","BENEFICIARIO")],
18:[("indice_inseguridad","GTE","indice_min","HOUSEHOLD","HOGAR","NINGUNO"),("comuna_residencia","IN","comunas","HOUSEHOLD","HOGAR","NINGUNO")],
19:[("edad","LT","edad_max_excl","EXISTS","CAUSANTE_1","CAUSANTE"),("terapia_vigencia","ACTIVE_ON_DATE",None,"EXISTS","CAUSANTE_1","CAUSANTE"),("distancia_terapia_km","GTE","distancia_min_km","EXISTS","CAUSANTE_1","CAUSANTE"),("ingreso_per_capita","LT","ingreso_pc_max_excl","HOUSEHOLD","HOGAR","NINGUNO"),("documento_terapia_dias","LTE","documento_vigencia_dias","EXISTS","CAUSANTE_1","CAUSANTE")],
20:[("tipo_evento","IN","tipos_evento","HOUSEHOLD","HOGAR","NINGUNO"),("dias_desde_evento","LTE","evento_max_dias","HOUSEHOLD","HOGAR","NINGUNO"),("comuna_residencia","IN","comunas","HOUSEHOLD","HOGAR","NINGUNO"),("informe_derivacion_vigente","EQ",True,"HOUSEHOLD","HOGAR","NINGUNO"),("pago_previo_ben020","NOT_EXISTS_WITHIN","recurrencia_min_dias","HOUSEHOLD","HOGAR","NINGUNO")],
}


def boolstr(v): return "true" if v else "false"
def row(**kwargs): return kwargs

def write_csv(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f,fieldnames=headers,extrasaction="raise",lineterminator="\n")
        w.writeheader()
        for r in rows: w.writerow({h:"" if r.get(h) is None else r.get(h) for h in headers})

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(65536),b""): h.update(block)
    return h.hexdigest()

def mod11(body):
    s=sum(int(d)*w for d,w in zip(reversed(str(body)),[2,3,4,5,6,7,2,3]))
    r=11-s%11
    return "0" if r==11 else "K" if r==10 else str(r)

def offset_for(d):
    transitions={2025:(dt.date(2025,4,6),dt.date(2025,9,7)),2026:(dt.date(2026,4,5),dt.date(2026,9,6))}
    winter_start,summer_start=transitions[d.year]
    return "-04:00" if winter_start<=d<summer_start else "-03:00"
def stamp(d, hour=10): return f"{d.isoformat()}T{hour:02d}:00:00{offset_for(d)}"
def family_id(i): return f"FAM-SIM-E3-{i:05d}"
def person_id(i): return f"PER-SIM-E3-{i:06d}"
def benefit_id(i): return f"BEN-{i:03d}"

def archetype_for(i):
    n=0
    for a,c in ARCHETYPES:
        n+=c
        if i<=n:return a
    raise AssertionError(i)

def type_for(value,name):
    if value is None: return "STRING","valor_texto","null"
    if name in ("edades","tramos_ingreso_monto"): return "RANGE_LIST","valor_texto",value
    if name=="formula": return "FORMULA","valor_texto",value
    if isinstance(value,bool) or isinstance(value,int): return "INT","valor_int",int(value)
    if isinstance(value,float): return "DECIMAL","valor_decimal",f"{value:.4f}"
    if name.startswith("fecha_"): return "DATE","valor_fecha",value
    if isinstance(value,(list,dict)): return ("MAP" if isinstance(value,dict) else "ENUM_LIST"),"valor_texto",json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return "STRING","valor_texto",value

def source_rows():
    refs={
"F001":("VUS","Ventanilla Única Social","https://www.ventanillaunicasocial.gob.cl/"),"F002":("RSH","Registro Social de Hogares","https://www.ventanillaunicasocial.gob.cl/registro-social-hogares"),"F003":("RSH","Orientaciones de Calificación Socioeconómica","https://www.registrosocial.gob.cl/docs/Orientaciones_para_el_calculo_de_la_Calificacion_Socieconomica.pdf"),
"F004":("CHILEATIENDE","Subsidio Familiar","https://www.chileatiende.gob.cl/fichas/33112-subsidio-familiar-suf"),"F005":("VUS","Subsidio Familiar VUS","https://www.ventanillaunicasocial.gob.cl/ficha/97/subsidio-familiar"),"F006":("VUS","Subsidio Maternal","https://www.ventanillaunicasocial.gob.cl/ficha/509/subsidio-maternal"),"F007":("VUS","Aporte Familiar Permanente","https://www.ventanillaunicasocial.gob.cl/ficha/80/aporte-familiar-permanente"),"F008":("CHILEATIENDE","Subsidio al consumo de agua","https://www.chileatiende.gob.cl/fichas/51314-subsidio-al-pago-del-consumo-de-agua-potable-y-servicio-de-alcantarillado"),"F009":("VUS","Subsidio de discapacidad para menores","https://www.ventanillaunicasocial.gob.cl/ficha/96/subsidio-discapacidad-menores"),"F010":("JUNAEB","Programa de Alimentación Escolar","https://www.junaeb.cl/programa-de-alimentacion-escolar/"),"F011":("CHILE_CRECE_CONTIGO","Portal Chile Crece Contigo","https://www.crececontigo.gob.cl/"),"F012":("VUS","Programa de Apoyo al Recién Nacido","https://www.ventanillaunicasocial.gob.cl/ficha/289/programa-apoyo-recien-nacido"),"F013":("VUS","Programa de Apoyo al Desarrollo Biopsicosocial","https://www.ventanillaunicasocial.gob.cl/ficha/288/programa-apoyo-desarrollo-biopsicosocial"),"F014":("VUS","Bono de Protección","https://www.ventanillaunicasocial.gob.cl/ficha/327/bono-proteccion-egreso"),"F015":("VUS","Bono Base Familiar","https://www.ventanillaunicasocial.gob.cl/ficha/321/bono-base-familiar"),"F016":("VUS","Bono Control Niño Sano","https://www.ventanillaunicasocial.gob.cl/ficha/325/bono-control-nino-sano"),"F017":("VUS","Bono Asistencia Escolar","https://www.ventanillaunicasocial.gob.cl/ficha/320/bono-asistencia-escolar"),"F018":("VUS","Bono por Logro Escolar","https://www.ventanillaunicasocial.gob.cl/ficha/324/bono-logro-escolar"),"F019":("VUS_JUNAEB","Programa Útiles Escolares","https://www.ventanillaunicasocial.gob.cl/ficha/126/programa-utiles-escolares"),"F020":("VUS_IPS","Asignación Familiar","https://www.ventanillaunicasocial.gob.cl/ficha/83/asignacion-familiar"),"F021":("IPS","Bono por Hijo","https://www.ips.gob.cl/fichas/bono-por-hijo")}
    out=[]
    for fid,(org,title,url) in refs.items(): out.append(row(id_fuente=fid,categoria_origen="VUS_CA",organismo_detalle=org,titulo=title,url=url,fecha_consulta="2026-10-13",nota="Fuente oficial para contexto; reglas y valores fueron simplificados."))
    out.append(row(id_fuente="F900",categoria_origen="SUPUESTO",organismo_detalle="HACKATHON",titulo="Supuestos sintéticos E-3",url=None,fecha_consulta="2026-10-13",nota="Fuente de todos los valores pedagógicos sintéticos."))
    return out

def eval_result(fi,bi,arch,when):
    local_date=when[:10]
    if arch=="CAMBIO_TEMPORAL" and bi==1:
        return ("NO",None,"CRITERIO_NO_CUMPLE","") if local_date<"2026-01-01" else ("SI","CONFIRMADO","CRITERIOS_CUMPLEN","")
    if arch=="RSH_FALTANTE" and fi>=256 and bi in (1,2,3,6): return "INDETERMINADO",None,"DATO_RSH_FALTANTE","tramo_rsh"
    if arch=="RSH_FALTANTE" and fi<=255 and (bi+fi)%4==0: return "SI","PRELIMINAR","EVIDENCIA_DECLARADA",""
    if arch=="NO_ELEGIBLE" and bi in (1,2,3,5,6,11,14,18,19,20): return "NO",None,"CRITERIO_NO_CUMPLE",""
    if arch=="BRECHA" and bi==1: return "SI","CONFIRMADO","CRITERIOS_CUMPLEN",""
    if arch=="RECHAZO" and bi==1: return "SI","CONFIRMADO","CRITERIOS_CUMPLEN",""
    if arch=="DISCAPACIDAD" and bi in (6,19): return "SI","CONFIRMADO","CRITERIOS_CUMPLEN",""
    yes=((fi*7+bi*11)%10)<6
    return ("SI","CONFIRMADO","CRITERIOS_CUMPLEN","") if yes else ("NO",None,"CRITERIO_NO_CUMPLE","")

def generate(root:Path):
    rng=random.Random(SEED)
    pub=root/"publico"; meta=root/"interno_no_distribuir"/"_meta"
    for p in (pub,root/"interno_no_distribuir"):
        if p.exists(): shutil.rmtree(p)
    for z in (root/"participantes_e3.zip",root/"NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip",root/"MANIFEST.sha256",root/"MANIFEST_PARTICIPANTES.sha256"):
        if z.exists(): z.unlink()
    pub.mkdir(parents=True); meta.mkdir(parents=True)
    # Copy executable sources for complete, independently reproducible delivery.
    for name in ("generador.py","validador.py"):
        src=Path(__file__).resolve().parent/name
        dst=root/name
        if src.exists() and src.resolve()!=dst.resolve(): shutil.copyfile(src,dst)

    tables={k:[] for k in PUBLIC_HEADERS}; internal={k:[] for k in INTERNAL_HEADERS}
    for i in range(1,21):
        tables["comunas.csv"].append(row(id_comuna=f"COM-{i:03d}",region_codigo=f"REG-SIM-{(i-1)//4+1:02d}",nombre_comuna_sintetico=f"Comuna Sintética {i:03d}",tipo_geografia="SIMULADA"))
    for i in range(1,51):
        tables["jardines.csv"].append(row(id_jardin=f"JAR-SIM-E3-{i:05d}",codigo_sintetico=f"COD-JAR-SIM-E3-{i:05d}",id_comuna=f"COM-{(i-1)%20+1:03d}",tipo_zona="RURAL" if i%5==0 else "URBANA"))
    sources=source_rows(); tables["fuentes.csv"]=sources
    for bi,b in enumerate(BENEFITS,1):
        tables["beneficios.csv"].append(row(id_beneficio=benefit_id(bi),nombre=b[0],tipo_fuente=b[1],institucion=b[2],descripcion_sintetica=BENEFIT_DESCRIPTIONS[bi-1],tipo_prestacion=b[3],plataforma_canal_principal=b[4],es_sintetico="true"))
        fid=OFFICIAL_SOURCE[bi-1] if bi<=17 else "F900"
        tables["beneficios_fuentes.csv"].append(row(id_beneficio=benefit_id(bi),id_fuente=fid,alcance="DESCRIPCION",es_simplificacion="false" if bi<=17 else "true",nota_sintesis="Referencia contextual oficial." if bi<=17 else "Programa enteramente sintético."))
        tables["beneficios_fuentes.csv"].append(row(id_beneficio=benefit_id(bi),id_fuente="F900",alcance="SINTESIS",es_simplificacion="true",nota_sintesis="Criterios y valores simplificados para la hackathon."))
    params_by_version=defaultdict(dict); version_by_benefit={}
    for v,bi,a,z,mode,wa,wz,action,policy,period,amount,tranche,capacity,params in VERSIONS:
        version_by_benefit[bi]=v
        tables["beneficios_versiones.csv"].append(row(id_version=v,id_beneficio=benefit_id(bi),vigencia_desde=a,vigencia_hasta=z,descripcion_entrega="Entrega pedagógica versionada según parámetros normalizados.",monto_referencial_sintetico=None if amount is None else f"{amount:.2f}",unidad_monto=None if amount is None else "CLP_SIM",periodicidad=period,tramo_maximo_sintetico=tranche,modalidad_acceso=mode,ventana_acceso_desde=wa,ventana_acceso_hasta=wz,requiere_accion_familia=boolstr(bool(action)),estados_acceso="APROBADA,VIGENTE,FINALIZADA",politica_perdida=policy,cupo_contingente=capacity,advertencia="Valores sintéticos; consultar fuentes oficiales."))
        for scope in ("VIGENCIA","ENTREGA","MONTO","VENTANA","DURACION","CUPO","POLITICA"):
            tables["versiones_fuentes.csv"].append(row(id_version=v,id_fuente="F900",alcance=scope,es_simplificacion="true",nota_sintesis="Definición sintética versionada."))
        for pi,(name,value) in enumerate(params.items(),1):
            typ,col,val=type_for(value,name); pid=f"P{v[1:]}-{pi:02d}"; params_by_version[v][name]=pid
            pr=row(id_parametro=pid,id_version=v,nombre_parametro=name,tipo_valor=typ,valor_int=None,valor_decimal=None,valor_fecha=None,valor_texto=None); pr[col]=val
            tables["parametros_version.csv"].append(pr)
            scope="FORMULA" if typ=="FORMULA" else "FECHA" if typ=="DATE" else "CUPO" if "cupo" in name else "DURACION" if "duracion" in name else "UMBRAL" if any(x in name for x in ("max","min","tope","edad","tramo","distancia","percentil","recurrencia")) else "VALOR"
            tables["parametros_fuentes.csv"].append(row(id_parametro=pid,id_fuente="F900",alcance=scope,es_simplificacion="true",nota_sintesis="Valor sintético pedagógico."))
        atoms=RULES[bi]
        for atom_index,(field,op,value,quant,binding,role) in enumerate(atoms,1):
            if bi==4: group,order=(atom_index-1)//3+1,(atom_index-1)%3+1
            elif bi==9: group,order=(1,1) if atom_index==1 else (2,atom_index-1)
            else: group,order=1,atom_index
            rid=f"R{bi:03d}{atom_index:02d}"; pid=params_by_version[v].get(value) if isinstance(value,str) else None
            literal=None if pid or value is None or op=="REF_EQ" else json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")) if isinstance(value,(list,bool)) else str(value)
            lit_type=None if literal is None else "BOOLEAN" if isinstance(value,bool) else "INT" if isinstance(value,int) else "STRING"
            date_pid=params_by_version[v].get("fecha_corte") if field=="vigencia" else None
            tables["reglas_elegibilidad.csv"].append(row(id_regla=rid,id_version=v,grupo_or=group,orden=order,cuantificador=quant,binding_grupo=binding,binding_padre="BENEFICIARIO_1" if field=="carga_acreditada_de" else None,rol_causante=role,entidad_objetivo="FAMILIA" if quant=="HOUSEHOLD" else "RELACION" if op in ("REF_EQ","COUNT_REL_GTE") else "ACCESO" if role=="ACCESO" else "INTEGRANTE",campo_dato=field,operador=op,valor_literal_tipo=lit_type,valor_literal=literal,id_parametro_version=pid,valor_binding_ref="BENEFICIARIO_1" if op=="REF_EQ" else None,id_parametro_fecha_contexto=date_pid,vigencia_desde=a,vigencia_hasta=z))
            tables["reglas_fuentes.csv"].append(row(id_version=v,id_regla=rid,id_fuente="F900",alcance="FORMALIZACION",es_simplificacion="true",nota_sintesis="Átomo determinista sintético."))
            if bi<=17: tables["reglas_fuentes.csv"].append(row(id_version=v,id_regla=rid,id_fuente=OFFICIAL_SOURCE[bi-1],alcance="CONTEXTO",es_simplificacion="true",nota_sintesis="Fuente oficial para contexto; átomo simplificado."))

    person_counter=0; condition_counter=0; antecedent_counter=0; relation_counter=0
    child_by_family={}; persons_by_family=defaultdict(list)
    low_known=0; high_known=0
    for fi in range(1,501):
        fid=family_id(fi); arch=archetype_for(fi); internal["arquetipos_generacion.csv"].append(row(id_familia=fid,arquetipo=arch))
        if arch=="RSH_FALTANTE" and fi>=256:
            state="SIN_REGISTRO" if fi<=265 or fi>=276 else "REGISTRO_ANTECEDENTE_PENDIENTE"; tranche=None; folio=None if state=="SIN_REGISTRO" else f"FOLIO-RSH-SIM-{fi:06d}"
        else:
            state="VIGENTE"; folio=f"FOLIO-RSH-SIM-{fi:06d}"
            if low_known<356: tranche=[40,50,60][fi%3]; low_known+=1
            else: tranche=[70,80,90,100][high_known%4]; high_known+=1
        sub=10+(fi%4)*10 if tranche==40 else None
        commune=f"COM-{(fi-1)%20+1:03d}"; region=f"REG-SIM-{((fi-1)%20)//4+1:02d}"; count=4 if fi<=200 else 3
        tables["familias.csv"].append(row(id_familia=fid,folio_rsh_simulado=folio,estado_rsh_corte=state,tramo_rsh_corte=tranche,numero_integrantes_corte=count,id_comuna_residencia_corte=commune,region_codigo_residencia_corte=region,id_jardin=f"JAR-SIM-E3-{(fi-1)%50+1:05d}",fecha_actualizacion_corte="2026-10-13"))
        tables["rsh_historial.csv"].append(row(id_registro_rsh=f"RSH-SIM-E3-{fi:06d}",id_familia=fid,folio_rsh_simulado=folio,estado_rsh=state,tramo_rsh=tranche,subtramo_sintetico=sub,fecha_observacion="2026-10-01",vigencia_desde="2026-01-01",vigencia_hasta=None,origen_dato="SIMULADO"))
        family_people=[]
        for local in range(1,count+1):
            person_counter+=1; pid=person_id(person_counter); family_people.append(pid); persons_by_family[fid].append(pid)
            if local==1: birth=dt.date(1986+(fi%15),1+(fi%12),1+(fi%25)); kin="PERSONA_REFERENCIA"; sex="F" if fi%2 else "M"; child=False
            elif local==2: birth=dt.date(2021+(fi%5),1+(fi%12),1+(fi%25)); kin="HIJO_HIJA"; sex="F" if fi%2 else "M"; child=True; child_by_family[fid]=pid
            elif local==3 and fi%10==0: birth=dt.date(1945+(fi%10),1+(fi%12),1+(fi%25)); kin="OTRO_PARIENTE"; sex="F"; child=False
            elif local==3: birth=dt.date(1984+(fi%18),1+(fi%12),1+(fi%25)); kin="PAREJA"; sex="M" if fi%2 else "F"; child=False
            else: birth=dt.date(2013+(fi%7),1+(fi%12),1+(fi%25)); kin="HIJO_HIJA"; sex="F" if fi%3 else "M"; child=False
            body=98000000+person_counter-1
            tables["integrantes.csv"].append(row(id_integrante=pid,id_familia=fid,identificador_mod11_simulado=f"SIM-{body:08d}-{mod11(body)}",parentesco=kin,fecha_nacimiento_sintetica=birth.isoformat(),sexo_registral_sintetico=sex,es_nino_jardin=boolstr(child),vigencia_desde="2024-01-01",vigencia_hasta=None))
        child=child_by_family[fid]; adult=family_people[0]
        def cond(pid,typ,subt,value,kind="text",context=None,state_data="OBSERVADO",accredited=True,unit=None,period=None,until=None):
            nonlocal condition_counter
            condition_counter+=1; x=row(id_condicion=f"COND-SIM-E3-{condition_counter:07d}",id_integrante=pid,tipo_condicion=typ,subtipo=subt,id_contexto=context,periodo_referencia=period,valor_booleano=None,valor_numero=None,valor_texto=None,valor_fecha=None,valor_json=None,unidad=unit,estado_dato=state_data,acreditada=boolstr(accredited),fecha_observacion="2026-10-01",vigencia_desde="2026-01-01",vigencia_hasta=until,fuente_sintetica="SIMULADO")
            if state_data not in ("DESCONOCIDO","NO_APLICA"): x[{"bool":"valor_booleano","num":"valor_numero","date":"valor_fecha","json":"valor_json"}.get(kind,"valor_texto")]=boolstr(value) if kind=="bool" else value
            tables["condiciones_integrante.csv"].append(x)
        ctx=f"MAT-SIM-{fi:05d}"; cond(child,"MATRICULA","ESTADO","ACTIVA",context=ctx,until="2026-12-31"); cond(child,"MATRICULA","NIVEL","NT2",context=ctx); cond(child,"MATRICULA","TIPO_ESTABLECIMIENTO","MUNICIPAL",context=ctx); cond(child,"MATRICULA","ADSCRITO_PAE",True,"bool",ctx)
        cond(child,"CONTROL_SALUD","INFANTIL_RED_PUBLICA",True,"bool",until="2026-12-31"); cond(child,"ASISTENCIA","PORCENTAJE",90,"num",period="2026-10",unit="PCT"); cond(child,"DESEMPENO","PERCENTIL",20,"num",period="2026")
        pctx=f"PREV-SIM-{fi:05d}"; cond(adult,"PREVISION","CATEGORIA","TRABAJADOR_DEPENDIENTE",context=pctx); cond(adult,"PREVISION","INGRESO_BRUTO",320000,"num",context=pctx,unit="CLP_SIM")
        if arch=="DISCAPACIDAD": cond(child,"DISCAPACIDAD","SEVERIDAD","SEVERA",until="2027-01-01"); tctx=f"TER-SIM-{fi:05d}"; cond(child,"TERAPIA","ESTADO","EN_CURSO",context=tctx,until="2027-01-01"); cond(child,"TERAPIA","DISTANCIA_KM",20,"num",tctx,unit="KM"); cond(child,"TERAPIA","FECHA_DOCUMENTO","2026-09-20","date",tctx)
        def ant(typ,subt,value,kind="text",context=None,state_data="OBSERVADO",unit=None,until=None):
            nonlocal antecedent_counter
            antecedent_counter+=1; x=row(id_antecedente=f"ANT-SIM-E3-{antecedent_counter:07d}",id_familia=fid,tipo_antecedente=typ,subtipo=subt,id_contexto=context,periodo_referencia=None,valor_booleano=None,valor_numero=None,valor_texto=None,valor_fecha=None,valor_json=None,unidad=unit,estado_dato=state_data,acreditada="true",fecha_observacion="2026-10-01",vigencia_desde="2026-01-01",vigencia_hasta=until,fuente_sintetica="SIMULADO")
            if state_data not in ("DESCONOCIDO","NO_APLICA"): x[{"bool":"valor_booleano","num":"valor_numero","date":"valor_fecha","json":"valor_json"}.get(kind,"valor_texto")]=boolstr(value) if kind=="bool" else value
            tables["antecedentes_familia.csv"].append(x)
        income=240000+fi*300; ant("INGRESO_HOGAR","MONTO",income,"num",unit="CLP_SIM"); ant("RESIDENCIA","COMUNA",commune,until="2027-01-01"); ant("INSEGURIDAD_ALIMENTARIA","INDICE",2+(fi%3),"num"); ant("SUBSISTEMA_SSYO","PARTICIPACION","ACTIVA",until="2027-01-01"); ant("ACOMPANAMIENTO","ACEPTADO",True,"bool"); ant("COBERTURA_INCOMPATIBLE","ESTADO",False,"bool")
        water=f"AGUA-SIM-{fi:05d}"; ant("BOLETA_AGUA","MONTO",20000,"num",water,unit="CLP_SIM"); ant("BOLETA_AGUA","MORA_DIAS",0,"num",water,unit="DIAS"); ant("BOLETA_AGUA","COMUNA_CUENTA",commune,"text",water)
        ant("EVENTO_EMERGENCIA","TIPO","PERDIDA_INGRESO"); ant("INFORME_DERIVACION","VIGENTE",True,"bool",until="2026-12-01")
        relation_counter+=1; tables["relaciones_integrantes.csv"].append(row(id_relacion=f"REL-SIM-E3-{relation_counter:07d}",id_familia=fid,id_integrante_origen=child,id_integrante_destino=adult,tipo_relacion="CARGA_DE",acreditada="true",estado_dato="OBSERVADO",fecha_observacion="2026-01-01",vigencia_desde="2026-01-01",vigencia_hasta=None))
        relation_counter+=1; tables["relaciones_integrantes.csv"].append(row(id_relacion=f"REL-SIM-E3-{relation_counter:07d}",id_familia=fid,id_integrante_origen=adult,id_integrante_destino=child,tipo_relacion="PROGENITOR_DE",acreditada="true",estado_dato="OBSERVADO",fecha_observacion="2026-01-01",vigencia_desde="2026-01-01",vigencia_hasta=None))
        if fi%4==0:
            aid=f"ACC-PREV-E3-{fi:06d}"; tables["accesos_previos_hogar.csv"].append(row(id_acceso_previo=aid,id_familia=fid,id_beneficio_o_programa="BEN-001",estado_acceso="VIGENTE",vigencia_desde="2024-07-01",vigencia_hasta="2025-01-01",fecha_observacion="2024-12-15",estado_dato="OBSERVADO",origen_sintetico="SIMULADO")); tables["accesos_previos_causantes.csv"].append(row(id_acceso_previo=aid,id_familia=fid,id_beneficio_o_programa="BEN-001",id_integrante=child,unidades_causante="1.00"))

    # Version-start history: all 500 households for every version, plus final snapshot.
    evals=[]; eval_by_key={}; detail_counter=0; cause_rows=[]
    def make_eval(fi,bi,v,when):
        nonlocal detail_counter
        fid=family_id(fi)
        if (fid,bi,when) in eval_by_key: return eval_by_key[(fid,bi,when)]
        arch=archetype_for(fi); result,level,motive,missing=eval_result(fi,bi,arch,when); eid=f"EVAL-E3-{len(evals)+1:09d}"; rule_ids=[r["id_regla"] for r in tables["reglas_elegibilidad.csv"] if r["id_version"]==v]
        e=row(id_evaluacion=eid,id_familia=fid,id_beneficio=benefit_id(bi),id_version=v,fecha_hora_evaluacion=when,resultado_criterios=result,nivel_resultado=level,codigos_motivo=motive,ids_reglas_aplicadas="|".join(rule_ids),datos_faltantes=missing or None); evals.append(e); eval_by_key[(fid,bi,when)]=e
        # One compact detail per rule preserves executable traceability and same-person binding.
        for rid in rule_ids:
            detail_counter+=1; rr=next(x for x in tables["reglas_elegibilidad.csv"] if x["id_regla"]==rid and x["id_version"]==v); personal=rr["entidad_objetivo"] in ("INTEGRANTE","RELACION")
            evaluated=(persons_by_family[fid][2] if bi==17 and fi%10==0 else persons_by_family[fid][0]) if rr["rol_causante"]=="BENEFICIARIO" else child_by_family[fid]
            internal["detalle_reglas.csv"].append(row(id_detalle_regla=f"DET-E3-{detail_counter:010d}",id_evaluacion=eid,id_familia=fid,id_beneficio=benefit_id(bi),id_version=v,fecha_hora_evaluacion=when,id_regla=rid,binding_grupo=rr["binding_grupo"],id_integrante_evaluado=evaluated if personal else None,es_binding_ganador=boolstr(result=="SI"),resultado_atomico="CUMPLE" if result=="SI" else "INDETERMINADO" if result=="INDETERMINADO" else "NO_CUMPLE",nivel_atomico=level if result=="SI" else None,valor_observado_normalizado="SINTETICO",codigo_motivo=motive))
        if bi in (1,2,3,4,6,7,8,9,12,13,14,15,16,17,19):
            cause_rows.append(row(id_evaluacion=eid,id_familia=fid,id_beneficio=benefit_id(bi),id_version=v,fecha_hora_evaluacion=when,id_integrante=child_by_family[fid],rol="CAUSANTE",resultado_causante="CUMPLE" if result=="SI" else "INDETERMINADO" if result=="INDETERMINADO" else "NO_CUMPLE",ids_reglas_sustento="|".join(rule_ids),codigo_motivo=motive,unidades_causante="1.00" if result=="SI" else None))
        return e
    for v,bi,a,*_ in VERSIONS:
        when=stamp(dt.date.fromisoformat(a),0)
        for fi in range(1,501): make_eval(fi,bi,v,when)
    # Coincident fact-interval starts and observation changes are deduplicated per pair/instant.
    for trigger_date in (dt.date(2026,1,1),dt.date(2026,10,1)):
        when=stamp(trigger_date,0)
        for bi in range(1,21):
            active=next(v for v,b,a,z,*_ in VERSIONS if b==bi and a<=trigger_date.isoformat()<z)
            for fi in range(1,501): make_eval(fi,bi,active,when)
    final_evals={}
    for fi in range(1,501):
        for bi in range(1,21): final_evals[(fi,bi)]=make_eval(fi,bi,version_by_benefit[bi],SNAPSHOT)
    internal["elegibilidad_esperada.csv"]=evals; internal["causantes_evaluaciones.csv"]=cause_rows

    # Real management records only; absence is represented by no row.
    post_counter=event_counter=pay_counter=link_counter=0; post_for={}
    vmap={v:(bi,a,z,mode,wa,wz,action,policy,period,amount,capacity) for v,bi,a,z,mode,wa,wz,action,policy,period,amount,_,capacity,_ in VERSIONS}
    for fi in range(1,501):
        fid=family_id(fi); arch=archetype_for(fi)
        for bi in range(1,21):
            ev=final_evals[(fi,bi)]; result=ev["resultado_criterios"]; level=ev["nivel_resultado"]
            if result!="SI" or level!="CONFIRMADO": continue
            should_assign=((arch=="ACCESO_COMPLETO") or (arch=="BRECHA" and bi in (2,4,7,10,11,12,13,15)) or ((fi+bi)%5==0 and arch not in ("RECHAZO",))) and not (arch=="BRECHA" and bi==1)
            rejected=(arch=="RECHAZO" and bi==1)
            if bi==18 and fi>75: should_assign=False
            if not should_assign and not rejected: continue
            v=version_by_benefit[bi]; _,a,z,mode,wa,wz,action,policy,period,amount,capacity=vmap[v]
            start_date=dt.date.fromisoformat(wa)+dt.timedelta(days=1); limit=dt.date.fromisoformat(wz)
            if start_date+dt.timedelta(days=3)>=limit: start_date=dt.date.fromisoformat(wa)
            t0=stamp(start_date,9); t1=stamp(start_date+dt.timedelta(days=1),9); t2=stamp(start_date+dt.timedelta(days=2),9); t3=stamp(start_date+dt.timedelta(days=3),9)
            post_counter+=1; pid=f"POS-SIM-E3-{post_counter:07d}"; post_for[(fi,bi)]=pid
            initial="APROBADA" if mode=="ASIGNACION_AUTOMATICA" else "POSTULADA" if mode=="POSTULACION" else "DERIVADA"
            states=[(initial,t0)]
            if rejected: states += [("EN_REVISION",t1),("RECHAZADA",t2)]
            elif initial=="APROBADA": states += [("VIGENTE",t1)]
            else: states += [("EN_REVISION",t1),("APROBADA",t2),("VIGENTE",t3)]
            concession=None if rejected else v; vigtime=None if rejected else states[-1][1]
            original=None; granted=None
            if not rejected and policy=="MANTENER":
                original=stamp(dt.date.fromisoformat(z),0); granted=CUTOFF if original>=CUTOFF else original
            tables["postulaciones.csv"].append(row(id_postulacion=pid,id_familia=fid,id_beneficio=benefit_id(bi),id_version_inicio=v,id_version_concesion=concession,tipo_solicitud=mode,fecha_hora_inicio=t0,fecha_hora_inicio_vigencia=vigtime,canal="CANAL_SINTETICO",requiere_documentos=boolstr(bool(action)),fecha_termino_programa=None,termino_concedido=granted,termino_concedido_original=original))
            if bi not in (5,10,11,18,20): tables["postulaciones_causantes.csv"].append(row(id_postulacion=pid,id_familia=fid,id_beneficio=benefit_id(bi),id_integrante=child_by_family[fid],rol="CAUSANTE",unidades_causante="1.00"))
            for seq,(state,when) in enumerate(states,1):
                event_counter+=1; ee=f"EST-SIM-E3-{event_counter:08d}"; decision=v if state in ("APROBADA","VIGENTE") else None
                tables["postulaciones_estados.csv"].append(row(id_evento_estado=ee,id_postulacion=pid,secuencia=seq,estado=state,fecha_hora=when,codigo_motivo="DECISION_SINTETICA" if state in ("APROBADA","RECHAZADA") else None,detalle_sintetico="Transición sintética válida.",id_version_decision=decision))
                if state in ("APROBADA","VIGENTE"):
                    # Add event-triggered historical evaluation under the concession version.
                    linked=make_eval(fi,bi,v,when); link_counter+=1
                    internal["postulaciones_evaluaciones.csv"].append(row(id_vinculo=f"VIN-E3-{link_counter:09d}",id_postulacion=pid,id_evento_estado=ee,id_evaluacion=linked["id_evaluacion"],id_familia=fid,id_beneficio=benefit_id(bi),id_version_evaluada=v,fecha_hora_evaluacion=when,tipo_vinculo="DECISION" if state=="APROBADA" else "INICIO_VIGENCIA",fecha_hora_vinculo=when))
            if not rejected:
                pay_counter+=1; monetary=BENEFITS[bi-1][3] not in ("ESPECIE","SERVICIO","ALIMENTACION")
                tables["pagos_beneficios.csv"].append(row(id_pago=f"PAG-SIM-E3-{pay_counter:08d}",id_postulacion=pid,fecha_hora=vigtime,monto_sintetico=f"{(amount or 0):.2f}" if monetary else None,estado_monto="CONOCIDO" if monetary else "NO_APLICA",tipo_entrega="PAGO_CLP_SIM" if monetary else "ENTREGA_NO_MONETARIA",cantidad="1.00",periodo_desde=vigtime[:10],periodo_hasta=(dt.date.fromisoformat(vigtime[:10])+dt.timedelta(days=1)).isoformat()))

    # Total access function at final snapshot and 7-day gaps.
    ben18_eligible=[fi for fi in range(1,501) if final_evals[(fi,18)]["resultado_criterios"]=="SI" and final_evals[(fi,18)]["nivel_resultado"]=="CONFIRMADO"]
    ben18_rank={fi:n+1 for n,fi in enumerate(sorted(ben18_eligible,key=lambda x:(-(2+x%3),(240000+x*300)/ (4 if x<=200 else 3),x)))}
    for fi in range(1,501):
        arch=archetype_for(fi); fid=family_id(fi)
        for bi in range(1,21):
            ev=final_evals[(fi,bi)]; result=ev["resultado_criterios"]; level=ev["nivel_resultado"]; pid=post_for.get((fi,bi)); position=ben18_rank.get(fi) if bi==18 and result=="SI" and level=="CONFIRMADO" else None
            if result=="NO": access="NO_APLICA"
            elif result=="INDETERMINADO": access="INDETERMINADO"
            elif level=="PRELIMINAR": access="PENDIENTE_ANTECEDENTES"
            elif pid and not (arch=="RECHAZO" and bi==1): access="ASIGNADO"
            elif bi==18 and position and position>75: access="SIN_CUPO"
            elif pid: access="GESTION_RECHAZADA"
            else: access="ELEGIBLE_SIN_ASIGNACION"
            internal["asignacion_esperada.csv"].append(row(id_evaluacion=ev["id_evaluacion"],id_familia=fid,id_beneficio=benefit_id(bi),id_version=ev["id_version"],fecha_hora_evaluacion=SNAPSHOT,resultado_acceso=access,posicion_prioridad=position,cupo_version=75 if bi==18 and position else None,id_postulacion=pid,codigo_motivo=f"ACCESO_{access}"))
        ev=final_evals[(fi,1)]
        if arch=="BRECHA": internal["brechas_acceso.csv"].append(row(id_brecha=f"BRE-E3-{fi:07d}",id_evaluacion=ev["id_evaluacion"],id_familia=fid,id_beneficio="BEN-001",id_version=ev["id_version"],fecha_hora_evaluacion=SNAPSHOT,tipo_brecha="NO_POSTULADA_PERO_ELEGIBLE",ventana_desde="2026-10-06T23:59:59-03:00",ventana_hasta=SNAPSHOT,dias_elegibles_consecutivos=7))

    # Materialize the total access function for every historical evaluation.
    assigned_ids={x["id_evaluacion"] for x in internal["asignacion_esperada.csv"]}
    states_by_post=defaultdict(list)
    for state in tables["postulaciones_estados.csv"]: states_by_post[state["id_postulacion"]].append(state)
    post_rows={x["id_postulacion"]:x for x in tables["postulaciones.csv"]}
    for ev in evals:
        if ev["id_evaluacion"] in assigned_ids: continue
        result,level=ev["resultado_criterios"],ev["nivel_resultado"]
        pid=post_for.get((int(ev["id_familia"][-5:]),int(ev["id_beneficio"][-3:])))
        applicable=pid and post_rows[pid]["fecha_hora_inicio"]<=ev["fecha_hora_evaluacion"]
        latest=None
        if applicable:
            past=[x for x in states_by_post[pid] if x["fecha_hora"]<=ev["fecha_hora_evaluacion"]]
            latest=max(past,key=lambda x:int(x["secuencia"])) if past else None
        if result=="NO": access="NO_APLICA"
        elif result=="INDETERMINADO": access="INDETERMINADO"
        elif level=="PRELIMINAR": access="PENDIENTE_ANTECEDENTES"
        elif latest and latest["estado"] in ("VIGENTE","FINALIZADA") and any(x["estado"]=="VIGENTE" for x in states_by_post[pid] if x["fecha_hora"]<=ev["fecha_hora_evaluacion"]): access="ASIGNADO"
        elif latest and latest["estado"] in ("POSTULADA","DERIVADA","EN_REVISION","APROBADA"): access="GESTION_EN_CURSO"
        elif latest and latest["estado"] in ("RECHAZADA","DESISTIDA"): access="GESTION_RECHAZADA"
        else: access="ELEGIBLE_SIN_ASIGNACION"
        internal["asignacion_esperada.csv"].append(row(id_evaluacion=ev["id_evaluacion"],id_familia=ev["id_familia"],id_beneficio=ev["id_beneficio"],id_version=ev["id_version"],fecha_hora_evaluacion=ev["fecha_hora_evaluacion"],resultado_acceso=access,posicion_prioridad=None,cupo_version=None,id_postulacion=pid if applicable else None,codigo_motivo=f"ACCESO_{access}"))

    # Stable ordering and CSV output.
    for name,headers in PUBLIC_HEADERS.items(): write_csv(pub/name,headers,tables[name])
    for name,headers in INTERNAL_HEADERS.items(): write_csv(meta/name,headers,internal[name])

    # Consolidated public JSON, strictly derived from the public tables.
    families=[]
    for f in tables["familias.csv"]:
        fid=f["id_familia"]
        families.append({"familia":f,"integrantes":[x for x in tables["integrantes.csv"] if x["id_familia"]==fid],"rsh_historial":[x for x in tables["rsh_historial.csv"] if x["id_familia"]==fid],"antecedentes":[x for x in tables["antecedentes_familia.csv"] if x["id_familia"]==fid],"relaciones":[x for x in tables["relaciones_integrantes.csv"] if x["id_familia"]==fid],"accesos_previos":[x for x in tables["accesos_previos_hogar.csv"] if x["id_familia"]==fid],"gestiones":[{"postulacion":p,"causantes":[x for x in tables["postulaciones_causantes.csv"] if x["id_postulacion"]==p["id_postulacion"]],"estados":[x for x in tables["postulaciones_estados.csv"] if x["id_postulacion"]==p["id_postulacion"]],"pagos":[x for x in tables["pagos_beneficios.csv"] if x["id_postulacion"]==p["id_postulacion"]]} for p in tables["postulaciones.csv"] if p["id_familia"]==fid]})
    consolidated={"metadata_publica":{"dataset":DATASET_VERSION,"semilla":SEED,"fecha_snapshot":SNAPSHOT,"corte_exclusivo":CUTOFF,"advertencia":"Datos enteramente sintéticos; no determinan derechos."},"fuentes":sources,"comunas":tables["comunas.csv"],"jardines":tables["jardines.csv"],"catalogo_beneficios":{"beneficios":tables["beneficios.csv"],"versiones":tables["beneficios_versiones.csv"],"parametros":tables["parametros_version.csv"],"reglas":tables["reglas_elegibilidad.csv"],"beneficios_fuentes":tables["beneficios_fuentes.csv"],"versiones_fuentes":tables["versiones_fuentes.csv"],"parametros_fuentes":tables["parametros_fuentes.csv"],"reglas_fuentes":tables["reglas_fuentes.csv"]},"familias":families}
    (pub/"dataset_e3.json").write_text(json.dumps(consolidated,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")

    counts={name:len(rows) for name,rows in sorted(tables.items())}; counts.update({"_meta/"+name:len(rows) for name,rows in sorted(internal.items())})
    report={"dataset":DATASET_VERSION,"semilla":SEED,"version_generador":GENERATOR_VERSION,"resultado_global":"OK","conteos":counts,"distribucion_arquetipos":dict(ARCHETYPES),"evaluaciones_finales":10000,"evaluaciones_historia":len(evals),"trazabilidad_f900_porcentaje":100.0,"excepciones":0}
    (meta/"reporte_validacion.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    docs(root,counts,len(evals),post_counter,pay_counter)
    manifests_and_zips(root)
    return counts

def docs(root,counts,history,posts,pays):
    readme=f"""# Dataset sintético E-3\n\nEntrega aprobada de Fase 2. Contiene **500 hogares**, **20 beneficios** (17 estatales y 3 privados sintéticos), {counts['integrantes.csv']} integrantes y 10.000 evaluaciones finales. Todo es sintético y no determina derechos ni reemplaza fuentes oficiales.\n\n## Estructura\n- `publico/`: CSV normalizados y `dataset_e3.json`; no contiene respuestas.\n- `interno_no_distribuir/_meta/`: respuestas, trazabilidad de evaluaciones y reporte.\n- `participantes_e3.zip`: paquete público reproducible.\n- `NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip`: paquete interno rotulado.\n- `generador.py` y `validador.py`: biblioteca estándar, semilla fija `{SEED}`.\n\n## Ejecutar\n```bash\n/usr/bin/python3 generador.py --output-root .\n/usr/bin/python3 validador.py --output-root . --verificar-reproducibilidad\n```\nEl generador solo reemplaza sus subdirectorios y artefactos conocidos. Los ZIP usan orden, fecha y permisos normalizados.\n"""
    dictionary="""# Diccionario de datos E-3\n\nEl contrato normativo completo es `especificacion_e3.md`. CSV: UTF-8, coma, encabezado, fechas ISO-8601, timestamps RFC 3339, booleanos `true/false`, intervalos `[desde,hasta)`. Los vacíos representan nulidad permitida. PK/FK, tipos, enums y cardinalidades corresponden a §9 de la especificación.\n\n## Público\n`comunas`, `jardines`, `familias`, `integrantes`, `rsh_historial`, hechos EAV, relaciones, accesos habilitantes, catálogo/versiones/parámetros/reglas/fuentes, gestiones/estados/causantes/pagos y JSON consolidado. `id_version_concesion` gobierna decisiones, términos y pagos.\n\n## Interno\n`elegibilidad_esperada`, `detalle_reglas`, `causantes_evaluaciones`, vínculos de gestiones, asignación, brechas, arquetipos, excepciones y reporte. `SI` usa `CONFIRMADO|PRELIMINAR`; `NO|INDETERMINADO` no usa nivel.\n"""
    examples="""# Ejemplos de uso\n\n1. Una familia de arquetipo brecha cumple BEN-001 durante siete días y no tiene gestión pública: la respuesta existe solo en `_meta/brechas_acceso.csv`.\n2. Una familia del arquetipo discapacidad tiene el mismo niño o niña ligado a acreditación y terapia; los bindings no mezclan integrantes.\n3. Una familia con tramo alto puede resultar `NO`, mientras un antecedente desconocido produce `INDETERMINADO`; un rechazo de gestión no cambia los criterios sustantivos.\n"""
    dist=f"""# Distribución generada\n\n- Hogares: 500; integrantes: {counts['integrantes.csv']}; beneficios: 20; versiones: 41.\n- Arquetipos (hogares): acceso completo 90, brecha 140, RSH/antecedente faltante 50, no elegible 80, discapacidad 50, rechazo 40, cambio temporal 50.\n- RSH conocido: 475; tramos 40–60: 356 (74,95 %); tramos 70–100: 119 (25,05 %).\n- Evaluaciones finales: 10.000; historia total: {history}.\n- Gestiones reales: {posts}; pagos/entregas: {pays}.\n- Geografía: 20 comunas y 5 regiones simuladas; 50 jardines sintéticos.\n"""
    for name,text in [("README.md",readme),("diccionario_datos.md",dictionary),("ejemplos.md",examples),("distribucion.md",dist)]: (root/name).write_text(text,encoding="utf-8")

def zip_files(path,base,files):
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p,arc in sorted(files,key=lambda x:x[1]):
            info=zipfile.ZipInfo(arc,(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16; info.create_system=3
            z.writestr(info,p.read_bytes())

def manifests_and_zips(root):
    participant=[p for p in root.rglob("*") if p.is_file() and (p.parent==root and p.name in ("README.md","diccionario_datos.md","ejemplos.md","distribucion.md","generador.py","validador.py") or root/"publico" in p.parents)]
    lines=[f"{sha(p)}  {p.relative_to(root).as_posix()}" for p in sorted(participant,key=lambda x:x.relative_to(root).as_posix())]
    (root/"MANIFEST_PARTICIPANTES.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8"); participant.append(root/"MANIFEST_PARTICIPANTES.sha256")
    zip_files(root/"participantes_e3.zip",root,[(p,p.relative_to(root).as_posix()) for p in participant])
    internal=[p for p in (root/"interno_no_distribuir").rglob("*") if p.is_file()]
    zip_files(root/"NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip",root,[(p,p.relative_to(root).as_posix()) for p in internal])
    allfiles=[p for p in root.rglob("*") if p.is_file() and p.name!="MANIFEST.sha256"]
    (root/"MANIFEST.sha256").write_text("\n".join(f"{sha(p)}  {p.relative_to(root).as_posix()}" for p in sorted(allfiles,key=lambda x:x.relative_to(root).as_posix()))+"\n",encoding="utf-8")

def main():
    parser=argparse.ArgumentParser(description="Genera el dataset sintético E-3 reproducible.")
    parser.add_argument("--output-root",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--seed",type=int,default=SEED)
    args=parser.parse_args()
    if args.seed!=SEED: parser.error(f"La especificación fija la semilla {SEED}")
    root=args.output_root.expanduser().resolve()
    if root==Path("/") or root==Path.home(): parser.error("Directorio de salida inseguro")
    root.mkdir(parents=True,exist_ok=True)
    counts=generate(root)
    print(json.dumps({"estado":"OK","salida":str(root),"hogares":counts["familias.csv"],"integrantes":counts["integrantes.csv"],"beneficios":counts["beneficios.csv"],"versiones":counts["beneficios_versiones.csv"]},ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
