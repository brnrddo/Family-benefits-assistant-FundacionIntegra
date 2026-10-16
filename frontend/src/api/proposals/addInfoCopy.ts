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
  /** add_info.optional_sensitive {question}: dentro de la leyenda, para que el lector de pantalla lo anuncie. */
  optionalSensitive: (question: string) => `${question} (si desea responder)`,
  /** add_info.q.<campo> */
  questions: {
    has_incompatible_coverage: '¿Recibe otro apoyo o cobertura que no se pueda juntar con este?',
    pregnancy_public_network_delivery: '¿El parto fue o será en la red pública de salud?',
    pregnancy_public_prenatal_control: '¿Lleva sus controles de embarazo en la red pública de salud?',
    residence_requirement_met: '¿La familia cumple el tiempo de residencia que pide el beneficio?',
    age_record_current: '¿Está al día el documento que acredita la edad?',
  },
  // --- Preguntas orientadas al caso (DEC-093) ---
  /** add_info.opens {names}: beneficios INDETERMINADO que esta respuesta puede destrabar. */
  opens: (names: string) => `Puede abrir: ${names}`,
  /** add_info.completes {names}: beneficios que ya aplican pero con antecedentes pendientes. */
  completes: (names: string) => `También ayuda con: ${names}`,
  /** add_info.more_questions {count} */
  moreQuestions: (count: string) => `Ver más preguntas (${count})`,
  /** add_info.fewer_questions */
  fewerQuestions: 'Ver menos preguntas',
  /** add_info.no_pending */
  noPending: 'No hay datos pendientes para esta familia.',
  /** add_info.other_benefit: beneficio sin título legible (nunca se muestra el código). */
  otherBenefit: 'Otro apoyo del catálogo',
  // Pista de contexto (1 línea) para recordar el caso: solo datos que la API ya entrega.
  /** add_info.hint.children_one {age} */
  hintChildOne: (age: string) => `1 niño o niña de ${age}`,
  /** add_info.hint.children_many {count} {age} */
  hintChildren: (count: string, age: string) => `${count} niños o niñas, el menor de ${age}`,
  /** add_info.hint.under_one_year */
  hintUnderOneYear: 'menos de 1 año',
  /** add_info.hint.rsh_band {band} */
  hintRshBand: (band: string) => `tramo ${band} % del Registro Social de Hogares`,
  /** add_info.hint.no_rsh_band */
  hintNoRshBand: 'sin tramo del Registro Social de Hogares en la ficha',
  /** add_info.hint.signal.<señal> (urgency_signals de /contexto) */
  hintSignal: {
    recent_emergency: 'con una emergencia reciente',
    precarious_housing: 'con vivienda precaria',
    limited_quota: 'en un apoyo con cupos limitados',
  },
  /** add_info.hint.family {facts} */
  hintFamily: (facts: string) => `En la ficha: ${facts}.`,
  /** add_info.hint.state.indeterminado {benefit} */
  hintStateUnknown: (benefit: string) => `Hoy ${benefit} queda sin definir por falta de este dato.`,
  /** add_info.hint.state.pending {benefit} */
  hintStatePending: (benefit: string) => `${benefit} ya aplica, pero falta este antecedente para postular.`,
  // --- Resultado tras guardar ---
  /** add_info.result_title */
  resultTitle: 'Resultado con los datos agregados',
  /** add_info.now_applies */
  nowApplies: 'Ahora aplica (preliminar, con datos declarados):',
  /** add_info.still_missing */
  stillMissing: 'Sigue faltando:',
  /** add_info.not_listed */
  notListed: 'Con estos datos ya no aparece como opción:',
  /** add_info.no_change */
  noChange: 'Con estos datos no cambió ningún apoyo.',
  /** add_info.back_to_family */
  backToFamily: 'Volver a la ficha',
  /** add_info.because_declared {items} */
  becauseDeclared: (items: string) => `con lo declarado: ${items}`,
  /** add_info.because_missing {items} */
  becauseMissing: (items: string) => `falta: ${items}`,
  /** add_info.field_short.<campo>: etiqueta corta del dato declarado en el resultado. */
  fieldShort: {
    child_age: 'Edad del niño o niña',
    siblings_under_6: 'Hermanos menores de 6 años',
    siblings_6_14: 'Hermanos de 6 a 14 años',
    siblings_15_18: 'Hermanos de 15 a 18 años',
    has_rsh: 'Registro Social de Hogares',
    rsh_band: 'Tramo del Registro Social de Hogares',
    household_income_band: 'Ingreso del hogar',
    ssyo_participation: 'Seguridades y Oportunidades',
    chile_crece_contigo_access: 'Chile Crece Contigo',
    last_child_health_control_date: 'Último control de salud',
    child_possible_disability: 'Posible discapacidad',
    child_in_therapy: 'Terapia',
    housing_type: 'Vivienda',
    household_pregnancy: 'Embarazo en el hogar',
    household_has_adult_over_65: 'Persona mayor de 65 años',
    household_formal_employment_or_pension: 'Trabajo formal o pensión',
    household_water_payment_difficulty: 'Dificultad para pagar el agua',
    household_food_purchase_difficulty: 'Dificultad para comprar alimentos',
    has_incompatible_coverage: 'Otra cobertura parecida',
    pregnancy_public_network_delivery: 'Parto en la red pública',
    pregnancy_public_prenatal_control: 'Controles de embarazo en la red pública',
    residence_requirement_met: 'Tiempo de residencia',
    age_record_current: 'Documento de edad al día',
  },
  /** add_info.weeks_short {weeks} (etiqueta corta en el resultado) */
  weeksShortN: (weeks: string) => `${weeks} semanas o más`,
  /** add_info.weeks_short_min */
  weeksShortMin: 'Semanas mínimas de embarazo',
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
    dias_desde_control: 'Fecha del último control de salud del niño o niña',
  },
} as const;
