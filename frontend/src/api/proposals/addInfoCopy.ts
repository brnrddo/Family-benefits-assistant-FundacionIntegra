// Textos de "Agregar información" para los códigos del motor (campos fuera de C3) y de la tarjeta
// "Datos del hogar" de la ficha.
/**
 * PROVISIONAL: excepción documentada a FE-004 (mismo criterio que TERRITORIAL_COPY); el catálogo i18n
 * está congelado en 407 claves (PREG-070). En la Tarea 7, Rol 4 los migra a content/i18n/es.json con
 * la clave indicada en cada comentario (`missingEngine.<código>` → `family.missing_engine.<código>`).
 */
export const ADD_INFO_COPY = {
  /** add_info.q.pregnancy_weeks_min (sin umbral conocido: nunca un número fijo). */
  pregnancyWeeksMin: '¿Tiene las semanas mínimas indicadas?',
  /** add_info.q.pregnancy_weeks_n {weeks} (integer). */
  pregnancyWeeksN: (weeks: string) => `¿Tiene ${weeks} semanas de embarazo o más?`,
  /** add_info.optional_sensitive */
  optionalSensitive: 'Si desea responder',
  /** add_info.q.<campo> */
  questions: {
    has_incompatible_coverage: '¿Recibe otro apoyo o cobertura que no se pueda juntar con este?',
    pregnancy_public_network_delivery: '¿El parto fue o será en la red pública de salud?',
    pregnancy_public_prenatal_control: '¿Lleva sus controles de embarazo en la red pública de salud?',
    residence_requirement_met: '¿La familia cumple el tiempo de residencia que pide el beneficio?',
    age_record_current: '¿Está al día el documento que acredita la edad?',
  },
  /** family.household_title */
  householdTitle: 'Datos del hogar',
  /** family.missing_engine.<código>: dato faltante del motor en lenguaje simple (sin el código). */
  missingEngine: {
    semanas_gestacion: 'Semanas de embarazo',
    cobertura_incompatible: 'Si tiene otra cobertura o apoyo parecido',
    tramo_rsh: 'Tramo del Registro Social de Hogares',
    parto_red_publica: 'Si el parto es en la red pública',
    control_prenatal_red_publica: 'Si los controles de embarazo son en la red pública',
    estado_acceso: 'Si ya recibe o tramita el apoyo',
    id_beneficio_o_programa: 'Qué programa o apoyo recibe',
    vigencia: 'Si el apoyo sigue vigente',
    discapacidad_severidad: 'Grado de la discapacidad',
    discapacidad_vigencia: 'Si el registro de discapacidad está vigente',
    dias_desde_nacimiento: 'Fecha del nacimiento',
    distancia_terapia_km: 'Distancia al lugar de la terapia',
    documento_terapia_dias: 'Documento de la terapia al día',
    terapia_vigencia: 'Si la terapia sigue vigente',
    dias_desde_evento: 'Fecha del hecho que origina el apoyo',
    pago_previo_ben020: 'Si ya recibió un pago de este apoyo',
    /** Cualquier `residencia_*`. */
    residencia: 'Tiempo de residencia',
    antecedente_edad_vigente: 'Documento que acredita la edad',
  },
} as const;
