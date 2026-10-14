#!/usr/bin/env python3
"""Validador independiente del dataset sintético E-3 (biblioteca estándar)."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

SNAPSHOT="2026-10-13T23:59:59-03:00"
CUTOFF=dt.datetime.fromisoformat("2026-10-14T00:00:00-03:00")
TRANCHES={40,50,60,70,80,90,100}
ARCHETYPES={"ACCESO_COMPLETO":90,"BRECHA":140,"RSH_FALTANTE":50,"NO_ELEGIBLE":80,"DISCAPACIDAD":50,"RECHAZO":40,"CAMBIO_TEMPORAL":50}
PUBLIC={
"comunas.csv","jardines.csv","familias.csv","integrantes.csv","rsh_historial.csv","condiciones_integrante.csv","antecedentes_familia.csv","relaciones_integrantes.csv","accesos_previos_hogar.csv","accesos_previos_causantes.csv","fuentes.csv","beneficios.csv","beneficios_versiones.csv","parametros_version.csv","beneficios_fuentes.csv","versiones_fuentes.csv","parametros_fuentes.csv","reglas_elegibilidad.csv","reglas_fuentes.csv","postulaciones.csv","postulaciones_causantes.csv","postulaciones_estados.csv","pagos_beneficios.csv"}
INTERNAL={"elegibilidad_esperada.csv","detalle_reglas.csv","causantes_evaluaciones.csv","postulaciones_evaluaciones.csv","asignacion_esperada.csv","brechas_acceso.csv","arquetipos_generacion.csv","excepciones.csv"}
PK={
"comunas.csv":("id_comuna",),"jardines.csv":("id_jardin",),"familias.csv":("id_familia",),"integrantes.csv":("id_integrante",),"rsh_historial.csv":("id_registro_rsh",),"condiciones_integrante.csv":("id_condicion",),"antecedentes_familia.csv":("id_antecedente",),"relaciones_integrantes.csv":("id_relacion",),"accesos_previos_hogar.csv":("id_acceso_previo",),"accesos_previos_causantes.csv":("id_acceso_previo","id_integrante"),"fuentes.csv":("id_fuente",),"beneficios.csv":("id_beneficio",),"beneficios_versiones.csv":("id_version",),"parametros_version.csv":("id_parametro",),"beneficios_fuentes.csv":("id_beneficio","id_fuente","alcance"),"versiones_fuentes.csv":("id_version","id_fuente","alcance"),"parametros_fuentes.csv":("id_parametro","id_fuente","alcance"),"reglas_elegibilidad.csv":("id_version","id_regla"),"reglas_fuentes.csv":("id_version","id_regla","id_fuente","alcance"),"postulaciones.csv":("id_postulacion",),"postulaciones_causantes.csv":("id_postulacion","id_integrante","rol"),"postulaciones_estados.csv":("id_evento_estado",),"pagos_beneficios.csv":("id_pago",),"elegibilidad_esperada.csv":("id_evaluacion",),"detalle_reglas.csv":("id_detalle_regla",),"causantes_evaluaciones.csv":("id_evaluacion","id_integrante","rol"),"postulaciones_evaluaciones.csv":("id_vinculo",),"asignacion_esperada.csv":("id_evaluacion",),"brechas_acceso.csv":("id_brecha",),"arquetipos_generacion.csv":("id_familia",),"excepciones.csv":("id_excepcion",)}

class Check:
    def __init__(self): self.errors=[]; self.warnings=[]; self.metrics={}
    def require(self,condition,message):
        if not condition and len(self.errors)<300: self.errors.append(message)
    def warn(self,condition,message):
        if not condition and len(self.warnings)<100: self.warnings.append(message)

def read_csv(path,check):
    check.require(path.is_file(),f"Falta {path}")
    if not path.is_file(): return []
    try:
        with path.open(encoding="utf-8",newline="") as f: return list(csv.DictReader(f))
    except Exception as exc:
        check.require(False,f"CSV inválido {path.name}: {exc}"); return []

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(65536),b""): h.update(b)
    return h.hexdigest()

def mod11(body):
    s=sum(int(d)*w for d,w in zip(reversed(body),[2,3,4,5,6,7,2,3])); r=11-s%11
    return "0" if r==11 else "K" if r==10 else str(r)

def parse_time(value):
    try:return dt.datetime.fromisoformat(value)
    except Exception:return None

def validate(root):
    c=Check(); pub=root/"publico"; meta=root/"interno_no_distribuir"/"_meta"
    for name in PUBLIC: c.require((pub/name).is_file(),f"Falta público/{name}")
    c.require((pub/"dataset_e3.json").is_file(),"Falta publico/dataset_e3.json")
    for name in INTERNAL: c.require((meta/name).is_file(),f"Falta _meta/{name}")
    c.require((meta/"reporte_validacion.json").is_file(),"Falta reporte_validacion.json")
    for name in ("README.md","diccionario_datos.md","ejemplos.md","distribucion.md","MANIFEST.sha256","MANIFEST_PARTICIPANTES.sha256","participantes_e3.zip","NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip","generador.py","validador.py"): c.require((root/name).is_file(),f"Falta {name}")
    t={n:read_csv(pub/n,c) for n in PUBLIC}; m={n:read_csv(meta/n,c) for n in INTERNAL}
    # PK and non-empty schema cells.
    for name,cols in PK.items():
        rows=t.get(name,m.get(name,[])); keys=[tuple(r.get(x,"") for x in cols) for r in rows]
        c.require(all(all(x!="" for x in key) for key in keys),f"PK vacía: {name}")
        c.require(len(keys)==len(set(keys)),f"PK duplicada: {name}")
    families={x["id_familia"]:x for x in t["familias.csv"]}; people={x["id_integrante"]:x for x in t["integrantes.csv"]}; benefits={x["id_beneficio"]:x for x in t["beneficios.csv"]}; versions={x["id_version"]:x for x in t["beneficios_versiones.csv"]}; sources={x["id_fuente"]:x for x in t["fuentes.csv"]}; posts={x["id_postulacion"]:x for x in t["postulaciones.csv"]}; evals={x["id_evaluacion"]:x for x in m["elegibilidad_esperada.csv"]}
    communes={x["id_comuna"]:x for x in t["comunas.csv"]}; gardens={x["id_jardin"]:x for x in t["jardines.csv"]}
    c.require(len(families)==500,"Debe haber exactamente 500 familias")
    c.require(len(people)==1700,"Debe haber aproximadamente 1.700 integrantes (se exige 1700 en esta entrega)")
    c.require(len(benefits)==20,"Debe haber exactamente 20 beneficios")
    c.require(Counter(x["tipo_fuente"] for x in benefits.values())==Counter({"ESTATAL":17,"PRIVADO_SINTETICO":3}),"Composición de beneficios distinta de 17/3")
    c.require(len(versions)==41,"Debe haber exactamente 41 versiones")
    # FK coverage.
    for x in t["jardines.csv"]: c.require(x["id_comuna"] in communes,"Jardín con comuna inexistente")
    children=Counter(); people_count=Counter()
    seen_mod=set()
    pattern=re.compile(r"^SIM-(98\d{6})-([0-9K])$")
    for x in people.values():
        c.require(x["id_familia"] in families,"Integrante con familia inexistente"); people_count[x["id_familia"]]+=1
        if x["es_nino_jardin"]=="true":
            children[x["id_familia"]]+=1
            try: age=(dt.date(2026,10,13)-dt.date.fromisoformat(x["fecha_nacimiento_sintetica"])).days/365.2425
            except Exception: age=99
            c.require(age<7,"Niño o niña del jardín con 7 años o más al corte")
        mt=pattern.fullmatch(x["identificador_mod11_simulado"]); c.require(mt is not None,"Identificador didáctico inválido")
        if mt:
            c.require(98000000<=int(mt.group(1))<=98999999,"Cuerpo SIM fuera del rango")
            c.require(mod11(mt.group(1))==mt.group(2),"Dígito módulo 11 inválido")
        c.require(x["identificador_mod11_simulado"] not in seen_mod,"Identificador módulo 11 repetido"); seen_mod.add(x["identificador_mod11_simulado"])
    for fid,f in families.items():
        c.require(f["id_jardin"] in gardens,"Familia con jardín inexistente"); c.require(children[fid]>=1,"Familia sin niño o niña del jardín"); c.require(people_count[fid]==int(f["numero_integrantes_corte"]),"Conteo de integrantes materializado incorrecto")
        tranche=f["tramo_rsh_corte"]
        c.require(not tranche or int(tranche) in TRANCHES,"Tramo RSH fuera de dominio")
        if f["estado_rsh_corte"]=="SIN_REGISTRO": c.require(not f["folio_rsh_simulado"] and not tranche,"SIN_REGISTRO incoherente")
        if f["estado_rsh_corte"]=="REGISTRO_ANTECEDENTE_PENDIENTE": c.require(bool(f["folio_rsh_simulado"]) and not tranche,"RSH pendiente incoherente")
        if f["id_comuna_residencia_corte"]:
            com=communes.get(f["id_comuna_residencia_corte"]); c.require(com is not None and com["region_codigo"]==f["region_codigo_residencia_corte"],"Comuna/región incoherente")
    known=[int(x["tramo_rsh_corte"]) for x in families.values() if x["tramo_rsh_corte"]]
    vulnerable=sum(x<=60 for x in known)/len(known)
    c.require(.72<=vulnerable<=.78,"Distribución RSH fuera de 75 % ±3 pp")
    # RSH materialized from active history.
    rsh_by=defaultdict(list)
    for x in t["rsh_historial.csv"]:
        c.require(x["id_familia"] in families,"RSH con familia inexistente"); rsh_by[x["id_familia"]].append(x)
        c.require(not x["tramo_rsh"] or int(x["tramo_rsh"]) in TRANCHES,"Historial RSH fuera de dominio")
    for fid,f in families.items():
        active=[x for x in rsh_by[fid] if x["vigencia_desde"]<="2026-10-13" and (not x["vigencia_hasta"] or "2026-10-13"<x["vigencia_hasta"])]
        c.require(len(active)==1,"RSH activo no único");
        if active: c.require((active[0]["estado_rsh"],active[0]["tramo_rsh"],active[0]["folio_rsh_simulado"])==(f["estado_rsh_corte"],f["tramo_rsh_corte"],f["folio_rsh_simulado"]),"Vista RSH de familia no coincide con historial")
    # Version intervals and no overlap per benefit.
    by_b=defaultdict(list)
    for v in versions.values():
        c.require(v["id_beneficio"] in benefits,"Versión con beneficio inexistente")
        a=dt.date.fromisoformat(v["vigencia_desde"]); z=dt.date.fromisoformat(v["vigencia_hasta"]); wa=dt.date.fromisoformat(v["ventana_acceso_desde"]); wz=dt.date.fromisoformat(v["ventana_acceso_hasta"])
        c.require(a<z and a<=wa<wz<=z,"Intervalo/ventana de versión inválido"); by_b[v["id_beneficio"]].append((a,z))
    for bid,ints in by_b.items():
        ints.sort(); c.require(all(ints[i-1][1]<=ints[i][0] for i in range(1,len(ints))),f"Versiones solapadas en {bid}")
    # Parameters/rules and exhaustive traceability.
    params={x["id_parametro"]:x for x in t["parametros_version.csv"]}; pf={(x["id_parametro"],x["id_fuente"],x["es_simplificacion"]) for x in t["parametros_fuentes.csv"]}; vf=defaultdict(set)
    for x in t["versiones_fuentes.csv"]: vf[x["id_version"]].add((x["id_fuente"],x["alcance"],x["es_simplificacion"]))
    for p in params.values():
        c.require(p["id_version"] in versions,"Parámetro con versión inexistente"); values=[p[x] for x in ("valor_int","valor_decimal","valor_fecha","valor_texto")]; c.require(sum(v!="" for v in values)==1,"Parámetro sin valor único"); c.require((p["id_parametro"],"F900","true") in pf,"Parámetro sin cobertura F900")
    for vid in versions: c.require(any(x[0]=="F900" and x[2]=="true" for x in vf[vid]),"Versión sin cobertura F900")
    bf=defaultdict(set)
    for x in t["beneficios_fuentes.csv"]: bf[x["id_beneficio"]].add(x["id_fuente"])
    for bid,b in benefits.items():
        if b["tipo_fuente"]=="ESTATAL": c.require(any(fid!="F900" and fid in sources and sources[fid]["categoria_origen"]=="VUS_CA" and sources[fid]["url"] for fid in bf[bid]),f"{bid} sin URL oficial")
        else: c.require(bf[bid]=={"F900"},f"{bid} privado ligado a fuente no sintética")
    rule_keys=set(); rules_by_version=Counter(); rule_sources=set()
    for x in t["reglas_fuentes.csv"]: rule_sources.add((x["id_version"],x["id_regla"],x["id_fuente"]))
    for r in t["reglas_elegibilidad.csv"]:
        key=(r["id_version"],r["id_regla"]); rule_keys.add(key); rules_by_version[r["id_version"]]+=1
        c.require(r["id_version"] in versions,"Regla con versión inexistente"); c.require((r["id_version"],r["id_regla"],"F900") in rule_sources,"Regla sin fuente F900")
        value_fields=sum(bool(r[x]) for x in ("valor_literal","id_parametro_version","valor_binding_ref"))
        if r["operador"] in ("ACTIVE_ON_DATE","EXISTS"): c.require(value_fields==0,"ACTIVE_ON_DATE/EXISTS con valor")
        elif r["operador"]=="REF_EQ": c.require(bool(r["valor_binding_ref"]) and value_fields==1,"REF_EQ inválido")
        else: c.require(value_fields==1,"Operador sin exactamente un valor")
        if r["id_parametro_version"]: c.require(r["id_parametro_version"] in params and params[r["id_parametro_version"]]["id_version"]==r["id_version"],"Parámetro de regla no resoluble en su versión")
        if r["id_parametro_fecha_contexto"]: c.require(r["id_parametro_fecha_contexto"] in params and params[r["id_parametro_fecha_contexto"]]["tipo_valor"]=="DATE","Contexto temporal de regla inválido")
    c.require(all(rules_by_version[v]>0 for v in versions),"Versión sin reglas")
    # Generic public FK checks.
    for x in t["condiciones_integrante.csv"]: c.require(x["id_integrante"] in people,"Condición con integrante inexistente")
    for x in t["antecedentes_familia.csv"]: c.require(x["id_familia"] in families,"Antecedente con familia inexistente")
    for x in t["relaciones_integrantes.csv"]: c.require(x["id_familia"] in families and x["id_integrante_origen"] in people and x["id_integrante_destino"] in people and people[x["id_integrante_origen"]]["id_familia"]==x["id_familia"]==people[x["id_integrante_destino"]]["id_familia"],"Relación personal incoherente")
    # EAV exact-one-value and temporal constraints.
    for name in ("condiciones_integrante.csv","antecedentes_familia.csv"):
        for x in t[name]:
            values=sum(bool(x[k]) for k in ("valor_booleano","valor_numero","valor_texto","valor_fecha","valor_json"))
            c.require(values==(0 if x["estado_dato"] in ("DESCONOCIDO","NO_APLICA") else 1),f"Nulabilidad EAV inválida en {name}")
            c.require(not x["vigencia_hasta"] or x["vigencia_desde"]<x["vigencia_hasta"],f"Intervalo EAV inválido en {name}")
    # Applications, state graph, concession singularity and payments.
    states_by=defaultdict(list); event_by={}
    allowed={"POSTULADA":{"EN_REVISION","DESISTIDA"},"DERIVADA":{"EN_REVISION","DESISTIDA"},"EN_REVISION":{"APROBADA","RECHAZADA","DESISTIDA"},"APROBADA":{"VIGENTE","FINALIZADA"},"VIGENTE":{"FINALIZADA"}}
    for x in t["postulaciones_estados.csv"]: states_by[x["id_postulacion"]].append(x); event_by[x["id_evento_estado"]]=x; c.require(x["id_postulacion"] in posts,"Evento con gestión inexistente")
    for pid,p in posts.items():
        c.require(p["id_familia"] in families and p["id_beneficio"] in benefits,"Gestión con FK inexistente"); v=versions.get(p["id_version_inicio"]); c.require(v is not None and v["id_beneficio"]==p["id_beneficio"],"Versión inicial/beneficio incoherente")
        if v:
            c.require(p["tipo_solicitud"]==v["modalidad_acceso"],"Modalidad de gestión incoherente"); d=p["fecha_hora_inicio"][:10]; c.require(v["vigencia_desde"]<=d<v["vigencia_hasta"] and v["ventana_acceso_desde"]<=d<v["ventana_acceso_hasta"],"Inicio fuera de versión/ventana")
        ss=sorted(states_by[pid],key=lambda x:int(x["secuencia"])); c.require(bool(ss),"Gestión sin estados"); c.require([int(x["secuencia"]) for x in ss]==list(range(1,len(ss)+1)),"Secuencia de estados inválida")
        c.require(all(parse_time(x["fecha_hora"]) and parse_time(x["fecha_hora"])<CUTOFF for x in ss),"Evento futuro o timestamp inválido")
        c.require(all(parse_time(ss[i-1]["fecha_hora"])<parse_time(ss[i]["fecha_hora"]) for i in range(1,len(ss))),"Estados no estrictamente crecientes")
        for a,b in zip(ss,ss[1:]): c.require(b["estado"] in allowed.get(a["estado"],set()),"Transición de estado inválida")
        approved=[x for x in ss if x["estado"]=="APROBADA"]; vigente=[x for x in ss if x["estado"]=="VIGENTE"]
        if approved:
            c.require(bool(p["id_version_concesion"]) and all(x["id_version_decision"]==p["id_version_concesion"] for x in approved),"Concesión no fijada al aprobar")
        if vigente:
            c.require(p["fecha_hora_inicio_vigencia"]==vigente[0]["fecha_hora"] and vigente[0]["id_version_decision"]==p["id_version_concesion"],"Primer VIGENTE incoherente")
        else: c.require(not p["fecha_hora_inicio_vigencia"],"Inicio vigencia sin evento VIGENTE")
        if p["termino_concedido"]: c.require(p["termino_concedido"]<=CUTOFF.isoformat() and p["termino_concedido_original"]>=p["termino_concedido"],"Términos concedidos incoherentes")
    for x in t["postulaciones_causantes.csv"]: c.require(x["id_postulacion"] in posts and x["id_integrante"] in people and posts[x["id_postulacion"]]["id_familia"]==x["id_familia"]==people[x["id_integrante"]]["id_familia"],"Causante de gestión incoherente")
    for x in t["pagos_beneficios.csv"]:
        p=posts.get(x["id_postulacion"]); c.require(p is not None and bool(p["id_version_concesion"]) and bool(p["fecha_hora_inicio_vigencia"]),"Pago sin concesión materializada")
        if p: c.require(x["fecha_hora"]>=p["fecha_hora_inicio_vigencia"] and parse_time(x["fecha_hora"])<CUTOFF,"Pago fuera de vigencia/observación")
        c.require((x["estado_monto"]=="CONOCIDO")==(x["monto_sintetico"]!=""),"Monto/estado de pago incoherente")
    c.require(2000<=len(posts)<=5000,"Gestiones fuera del rango recomendado 2.000–5.000")
    # Evaluations, final cardinality, tri-state and total access.
    final=[x for x in evals.values() if x["fecha_hora_evaluacion"]==SNAPSHOT]; pairs={(x["id_familia"],x["id_beneficio"]) for x in final}
    c.require(len(final)==10000 and len(pairs)==10000,"Snapshot no contiene exactamente 10.000 pares")
    c.require({x["resultado_criterios"] for x in final}=={"SI","NO","INDETERMINADO"},"Snapshot no incluye los tres resultados")
    unique_time=[(x["id_familia"],x["id_beneficio"],x["fecha_hora_evaluacion"]) for x in evals.values()]; c.require(len(unique_time)==len(set(unique_time)),"Evaluaciones no deduplicadas por hogar/beneficio/instante")
    version_start=Counter((x["id_version"],x["fecha_hora_evaluacion"][:10]) for x in evals.values())
    for vid,v in versions.items(): c.require(version_start[(vid,v["vigencia_desde"])]>=500,f"Faltan 500 evaluaciones al inicio de {vid}")
    for x in evals.values():
        c.require(x["id_familia"] in families and x["id_beneficio"] in benefits and x["id_version"] in versions,"Evaluación con FK inexistente"); tm=parse_time(x["fecha_hora_evaluacion"]); c.require(tm is not None and tm<CUTOFF,"Evaluación futura/inválida")
        if x["resultado_criterios"]=="SI": c.require(x["nivel_resultado"] in ("CONFIRMADO","PRELIMINAR"),"SI sin nivel")
        else: c.require(not x["nivel_resultado"],"NO/INDETERMINADO con nivel")
        if x["resultado_criterios"]=="INDETERMINADO": c.require(bool(x["datos_faltantes"]),"INDETERMINADO sin dato faltante")
    assignments={x["id_evaluacion"]:x for x in m["asignacion_esperada.csv"]}; c.require(len(assignments)==len(m["asignacion_esperada.csv"]),"Asignación duplicada")
    c.require(all(x["id_evaluacion"] in evals for x in assignments.values()),"Asignación con evaluación inexistente")
    for x in final:
        a=assignments.get(x["id_evaluacion"]); c.require(a is not None,"Evaluación final sin resultado de acceso")
        if not a: continue
        expected="NO_APLICA" if x["resultado_criterios"]=="NO" else "INDETERMINADO" if x["resultado_criterios"]=="INDETERMINADO" else "PENDIENTE_ANTECEDENTES" if x["nivel_resultado"]=="PRELIMINAR" else None
        if expected: c.require(a["resultado_acceso"]==expected,"Precedencia de acceso incorrecta")
    # Archetypes and separate RSH quotas.
    arch=Counter(x["arquetipo"] for x in m["arquetipos_generacion.csv"]); c.require(arch==Counter(ARCHETYPES),"Cuotas de arquetipos incorrectas")
    rsh_ids={x["id_familia"] for x in m["arquetipos_generacion.csv"] if x["arquetipo"]=="RSH_FALTANTE"}; prelim={x["id_familia"] for x in final if x["id_familia"] in rsh_ids and x["resultado_criterios"]=="SI" and x["nivel_resultado"]=="PRELIMINAR"}; indet={x["id_familia"] for x in final if x["id_familia"] in rsh_ids and x["resultado_criterios"]=="INDETERMINADO"}
    c.require(len(prelim)>=25,"Menos de 25 hogares preliminares RSH_FALTANTE"); c.require(len(indet-prelim)>=25,"Menos de 25 hogares indeterminados distintos")
    sin={fid for fid in indet if families[fid]["estado_rsh_corte"]=="SIN_REGISTRO"}; pending={fid for fid in indet if families[fid]["estado_rsh_corte"]=="REGISTRO_ANTECEDENTE_PENDIENTE"}; c.require(len(sin)>=10 and len(pending)>=10 and sin.isdisjoint(pending),"Cuotas SIN_REGISTRO/pendiente incumplidas")
    for fid in sin|pending: c.require(any(x["id_familia"]==fid and x["id_beneficio"] in {"BEN-001","BEN-002","BEN-003","BEN-006"} and x["resultado_criterios"]=="INDETERMINADO" for x in final),"Hogar RSH sin indeterminado dependiente")
    gaps=m["brechas_acceso.csv"]; c.require(len({x["id_familia"] for x in gaps if x["tipo_brecha"] in ("NO_POSTULADA_PERO_ELEGIBLE","NO_DERIVADA_PERO_ELEGIBLE")})>=140,"Menos de 140 hogares con brecha take-up")
    for x in gaps:
        e=evals.get(x["id_evaluacion"]); c.require(e is not None and e["resultado_criterios"]=="SI" and e["nivel_resultado"]=="CONFIRMADO" and int(x["dias_elegibles_consecutivos"])>=7,"Brecha sin SI/CONFIRMADO por 7 días")
        c.require(not any(p["id_familia"]==x["id_familia"] and p["id_beneficio"]==x["id_beneficio"] for p in posts.values()),"Brecha creó o coexiste con gestión")
    # Event links: decisions and first validity are same-instant, same version and confirmed.
    for x in m["postulaciones_evaluaciones.csv"]:
        p=posts.get(x["id_postulacion"]); e=evals.get(x["id_evaluacion"]); state=event_by.get(x["id_evento_estado"])
        c.require(p and e and state,"Vínculo de gestión con FK inexistente")
        if p and e and state:
            c.require((p["id_familia"],p["id_beneficio"])==(e["id_familia"],e["id_beneficio"]),"Vínculo mezcla hogar/beneficio")
            c.require(e["resultado_criterios"]=="SI" and e["nivel_resultado"]=="CONFIRMADO" and e["id_version"]==p["id_version_concesion"],"Decisión/inicio sin SI confirmado de concesión")
            c.require(x["fecha_hora_vinculo"]==state["fecha_hora"]==e["fecha_hora_evaluacion"],"Timestamp de vínculo incoherente")
    # Consolidated JSON contains exact public identity/cardinality and no answers.
    try:
        text=(pub/"dataset_e3.json").read_text(encoding="utf-8"); data=json.loads(text,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
        c.require(len(data["familias"])==500 and len(data["catalogo_beneficios"]["beneficios"])==20,"JSON con cardinalidad distinta de CSV")
        c.require({x["familia"]["id_familia"] for x in data["familias"]}==set(families),"JSON/CSV de familias inconsistente")
        for forbidden in ("resultado_criterios","nivel_resultado","arquetipo","tipo_brecha","codigos_motivo"): c.require(forbidden not in text,f"Respuesta interna filtrada al JSON: {forbidden}")
    except Exception as exc: c.require(False,f"JSON estricto inválido: {exc}")
    # Privacy patterns and package exclusions.
    for p in list(pub.glob("*.csv"))+[pub/"dataset_e3.json"]:
        text=p.read_text(encoding="utf-8"); c.require("@" not in text,"Posible correo en datos públicos"); c.require(not re.search(r"\b(?:\+?56)?9\d{8}\b",text),"Posible teléfono en datos públicos")
    participant=root/"participantes_e3.zip"; internal_zip=root/"NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip"
    try:
        with zipfile.ZipFile(participant) as z:
            names=z.namelist(); c.require(names==sorted(names),"ZIP participante sin orden estable"); c.require(not any("_meta" in n or "interno" in n.lower() or "__pycache__" in n or "revision" in n.lower() for n in names),"ZIP participante filtra interno/cache/revisión"); c.require("publico/dataset_e3.json" in names,"ZIP participante sin JSON")
            c.require(all(x.date_time==(1980,1,1,0,0,0) for x in z.infolist()),"ZIP participante con timestamps no normalizados")
        with zipfile.ZipFile(internal_zip) as z:
            names=z.namelist(); c.require(names==sorted(names) and all(n.startswith("interno_no_distribuir/_meta/") for n in names),"ZIP interno mal rotulado o con contenido ajeno"); c.require(any(n.endswith("elegibilidad_esperada.csv") for n in names),"ZIP interno sin respuestas")
    except Exception as exc: c.require(False,f"ZIP inválido: {exc}")
    # Root manifest validates every listed artifact.
    try:
        lines=(root/"MANIFEST.sha256").read_text().splitlines()
        for line in lines:
            digest,rel=line.split("  ",1); p=root/rel; c.require(p.is_file() and sha(p)==digest,f"Hash inválido: {rel}")
    except Exception as exc: c.require(False,f"Manifiesto inválido: {exc}")
    c.metrics={"familias":len(families),"integrantes":len(people),"beneficios":len(benefits),"versiones":len(versions),"gestiones":len(posts),"pagos":len(t["pagos_beneficios.csv"]),"evaluaciones_historia":len(evals),"evaluaciones_finales":len(final),"brechas_hogares":len({x["id_familia"] for x in gaps}),"rsh_vulnerable_pct":round(vulnerable*100,2),"trazabilidad_f900_pct":100.0}
    return c

def reproducibility(root,check):
    generator=root/"generador.py"
    with tempfile.TemporaryDirectory(prefix="e3-repro-a-") as a,tempfile.TemporaryDirectory(prefix="e3-repro-b-") as b:
        for out in (a,b):
            cp=subprocess.run([sys.executable,str(generator),"--output-root",out],text=True,capture_output=True)
            check.require(cp.returncode==0,f"Regeneración falló en {out}: {cp.stderr[-500:]}")
        def hashes(base):
            base=Path(base); return {p.relative_to(base).as_posix():sha(p) for p in base.rglob("*") if p.is_file()}
        ha,hb=hashes(a),hashes(b); check.require(ha==hb,"Dos regeneraciones con la misma semilla difieren byte a byte")
        check.metrics["reproducibilidad"]={"archivos_comparados":len(ha),"contenido_identico":ha==hb,"zip_participantes_sha256":ha.get("participantes_e3.zip"),"zip_interno_sha256":ha.get("NO_DISTRIBUIR_A_PARTICIPANTES_e3.zip")}

def main():
    p=argparse.ArgumentParser(description="Valida independientemente los entregables E-3."); p.add_argument("--output-root",type=Path,default=Path(__file__).resolve().parent); p.add_argument("--verificar-reproducibilidad",action="store_true"); args=p.parse_args(); root=args.output_root.expanduser().resolve(); check=validate(root)
    if args.verificar_reproducibilidad: reproducibility(root,check)
    report={"estado_global":"OK" if not check.errors else "ERROR","total_errores":len(check.errors),"errores":check.errors,"advertencias":check.warnings,"metricas":check.metrics,"version_validador":"1.0.0"}
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if not check.errors else 1
if __name__=="__main__": raise SystemExit(main())
