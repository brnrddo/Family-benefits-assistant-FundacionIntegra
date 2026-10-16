// Textos nuevos de la ficha: secciones de beneficios, filtro, faltantes concretos y "Qué hacer ahora".
/**
 * PROVISIONAL: misma excepción a FE-004 que ADD_INFO_COPY (catálogo i18n congelado, PREG-070). En la
 * Tarea 7, Rol 4 los migra a content/i18n/es.json con la clave indicada en cada comentario.
 * Nunca "le corresponde", "podría calificar" ni "vale la pena consultar".
 */
export const FAMILY_COPY = {
  /** family.section.apply */
  sectionApply: 'Puede postular ahora',
  /** family.section.missing */
  sectionMissing: 'Falta información',
  /** family.section.done */
  sectionDone: 'Ya postuló o sin cupo',
  /** family.section.done_show */
  showDone: 'Ver los que ya postuló o sin cupo',
  /** family.section.done_hide */
  hideDone: 'Ocultar',
  /** family.filter.legend */
  filterLegend: 'Mostrar',
  /** family.filter.all */
  filterAll: 'Todos',
  /** family.filter.apply {n} */
  filterApply: (n: string) => `Aplica (${n})`,
  /** family.filter.missing {n} */
  filterMissing: (n: string) => `Falta info (${n})`,
  /** family.filter.done {n} */
  filterDone: (n: string) => `Ya postuló o sin cupo (${n})`,
  /** family.missing_label */
  missingLabel: 'Falta saber:',
  /** family.benefit_guide {name} {labels}: datos sin pregunta Sí/No, con el beneficio al que pertenecen. */
  benefitGuide: (name: string, labels: readonly string[]) =>
    `${name}: ${labels.map((label) => label.charAt(0).toLocaleLowerCase('es') + label.slice(1)).join(' · ')}`,
  /** family.unknown_detail: respaldo para INDETERMINADO sin códigos con texto. */
  unknownDetail: 'Un dato que la ficha todavía no registra',
  /** family.plan.title */
  planTitle: 'Qué hacer ahora',
  /** family.plan.ask */
  planAsk: 'Toque Agregar información y pregúntele a la apoderada. Si usted ya lo sabe, respóndalo directamente.',
  /** family.plan.ask_no_form */
  planAskNoForm: 'Pregúntele a la apoderada:',
  /** family.plan.deliver {names} */
  planDeliver: (names: string) => `Entréguele la información de: ${names}`,
  /** family.plan.none */
  planNone: 'Esta familia no tiene acciones pendientes.',
} as const;
