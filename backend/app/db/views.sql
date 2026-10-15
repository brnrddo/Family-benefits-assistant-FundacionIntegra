-- Vistas de cruce del Rol 1 (spec §2.6, §3 M1).
-- Se apoyan en las tablas materializadas por el precálculo (build_views.py):
--   evaluaciones(id_familia, id_beneficio, id_version, resultado, nivel,
--                monto_estimado, datos_faltantes, motivos, entidad_ganadora, traza_json)
--   accesos(id_familia, id_beneficio, estado, semaforo, preliminar,
--           tiene_gestion, ultimo_estado_gestion, requiere_accion_familia,
--           modalidad_acceso, canal, ventana_desde, ventana_hasta, fuente_url)
--
-- Idempotente: se puede volver a ejecutar (DROP VIEW IF EXISTS primero).

-- La marca __FECHA_EVAL__ la sustituye build_views.py por la fecha de
-- evaluación del snapshot (p. ej. 2026-10-13) antes de ejecutar este script.

DROP VIEW IF EXISTS v_familia_beneficio;
DROP VIEW IF EXISTS v_oportunidades;
DROP VIEW IF EXISTS v_brechas;
DROP VIEW IF EXISTS v_ventanas;

-- 1) Una fila por (familia, beneficio): cruce elegibilidad + acceso + catálogo.
CREATE VIEW v_familia_beneficio AS
SELECT
    e.id_familia,
    e.id_beneficio,
    b.nombre                       AS beneficio_nombre,
    b.institucion,
    e.id_version,
    e.resultado,
    e.nivel,
    e.monto_estimado,
    a.estado                       AS estado_acceso,
    a.semaforo,
    a.preliminar,
    a.tiene_gestion,
    a.ultimo_estado_gestion,
    a.requiere_accion_familia,
    a.modalidad_acceso,
    a.canal,
    a.ventana_desde,
    a.ventana_hasta,
    a.fuente_url,
    e.datos_faltantes,
    e.motivos
FROM evaluaciones e
JOIN beneficios b   ON b.id_beneficio = e.id_beneficio
LEFT JOIN accesos a ON a.id_familia = e.id_familia AND a.id_beneficio = e.id_beneficio;

-- 2) Oportunidades: lo accionable para conversar con la familia.
--    Incluye los estados "verdes/amarillos" que ameritan acción u orientación,
--    excluye lo que ya tiene / está en trámite / no aplica.
CREATE VIEW v_oportunidades AS
SELECT *
FROM v_familia_beneficio
WHERE estado_acceso IN (
    'ELEGIBLE_SIN_ASIGNACION',
    'GESTION_RECHAZADA',
    'PENDIENTE_ANTECEDENTES',
    'INDETERMINADO',
    'SIN_CUPO'
);

-- 3) Brechas: la brecha estrella (califica confirmado y nunca lo pidió).
CREATE VIEW v_brechas AS
SELECT *
FROM v_familia_beneficio
WHERE estado_acceso = 'ELEGIBLE_SIN_ASIGNACION';

-- 4) Ventanas de inscripción: días hasta el cierre por (familia, beneficio).
--    Insumo para el eje Urgencia del Rol 2 (§8.1). NO pondera por sí sola.
--
--    ⚠️ Caveat de datos (§8.1): casi todas las versiones vigentes cierran el
--    mismo día (2026-10-14), así que a la fecha de evaluación casi todo tiene
--    dias_hasta_cierre = 1. Por eso se expone `ventana_discrimina`: es 1 solo
--    cuando el cierre del beneficio es DISTINTO del cierre más común entre las
--    oportunidades (es decir, cuando la ventana realmente aporta información).
--    Rol 2 debe mantener la señal de ventana configurable y apagada por
--    defecto (usar_ventana=false) mientras el dataset tenga este sesgo.
--
--    Solo tiene sentido para lo accionable (oportunidades): si ya lo tiene o no
--    aplica, la ventana es irrelevante.
CREATE VIEW v_ventanas AS
WITH cierre_comun AS (
    SELECT ventana_hasta
    FROM v_oportunidades
    WHERE ventana_hasta IS NOT NULL
    GROUP BY ventana_hasta
    ORDER BY COUNT(*) DESC
    LIMIT 1
)
SELECT
    o.id_familia,
    o.id_beneficio,
    o.beneficio_nombre,
    o.estado_acceso,
    o.requiere_accion_familia,
    o.ventana_desde,
    o.ventana_hasta,
    CASE
        WHEN o.ventana_hasta IS NULL THEN NULL
        ELSE CAST(julianday(o.ventana_hasta) - julianday('__FECHA_EVAL__') AS INTEGER)
    END                                              AS dias_hasta_cierre,
    CASE
        WHEN o.ventana_hasta IS NULL THEN 0
        WHEN o.ventana_hasta = (SELECT ventana_hasta FROM cierre_comun) THEN 0
        ELSE 1
    END                                              AS ventana_discrimina
FROM v_oportunidades o;
