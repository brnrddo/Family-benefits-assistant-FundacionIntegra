// Selección DETERMINISTA de preguntas de "Agregar información" orientada al caso (DEC-093). Sin React
// y sin LLM: el motor decide elegibilidad; aquí solo se eligen y ordenan preguntas a partir de los
// `missing_codes` que ya entrega C3 y del orden `position` del motor (no se reordena por puntaje,
// FE-003). Las pistas de contexto se arman con datos de la ficha y de /contexto, nunca con códigos.
import { DEPENDENT_FIELDS, fieldForMissingCode } from '../../api/proposals/addInfo';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { AddInfoField } from '../../api/proposals/types';
import type { FamilyContextView, FamilyDetail, Opportunity } from '../../api/types';
import { benefitSections, familyMissingCodes, groupBenefits, uniqueTexts, type BenefitRow } from '../../domain/benefitGroups';
import { formatInteger } from '../../domain/format';
import { knownMissingLabels, missingCodeLabels } from '../../domain/presentation';
import { benefitName, yearsLabel } from '../../i18n/copy';
import { QUESTION_ORDER, type AddInfoQuestionKey } from '../new-family/questions';

/** Preguntas principales visibles; el resto va tras "Ver más preguntas". */
export const MAX_PRIMARY_QUESTIONS = 3;

export interface PlannedQuestion {
  readonly key: AddInfoQuestionKey;
  /** Preguntas que dependen de esta (semanas tras embarazo; tramo tras "¿Tiene RSH?"). No cuentan en el tope. */
  readonly dependents: readonly AddInfoQuestionKey[];
  /** Nombres legibles de beneficios INDETERMINADO que puede destrabar (orden del motor). */
  readonly opens: readonly string[];
  /** Nombres legibles de beneficios SI con antecedentes pendientes que también completa. */
  readonly completes: readonly string[];
  /** Pista de una línea para recordar el caso (sin códigos ni nombres); null si repite la de una pregunta anterior. */
  readonly hint: string | null;
}

export interface QuestionPlan {
  readonly primary: readonly PlannedQuestion[];
  readonly more: readonly PlannedQuestion[];
  /** Filas de la sección "Falta información" de la ficha. 0 ⇒ nada pendiente. */
  readonly pendingBenefits: number;
  /** Datos sin campo cerrado: solo guía, sin repetir. */
  readonly guide: readonly string[];
}

const ID_PATTERN = /\b(BEN|FAM)-/;

/** Nombre legible: `simple_title` → i18n `benefit.<id>.name` → genérico. Nunca el código interno. */
export function readableBenefitName(row: BenefitRow): string {
  const name = benefitName(row.benefitId, row.simpleTitle);
  return name === row.benefitId || ID_PATTERN.test(name) ? ADD_INFO_COPY.otherBenefit : name;
}

/** Campo padre de un campo dependiente (semanas → embarazo), si lo hay. */
export function parentOf(key: AddInfoQuestionKey): AddInfoQuestionKey | null {
  for (const [parent, children] of Object.entries(DEPENDENT_FIELDS)) {
    if (children?.includes(key)) return parent as AddInfoQuestionKey;
  }
  return null;
}

/** Guía: preguntas de C3 de beneficios cuyos faltantes no tienen campo cerrado + etiquetas simples, sin repetir. */
function guideFor(detail: FamilyDetail, opportunities: readonly Opportunity[]): string[] {
  const { applies, missing } = groupBenefits(detail, opportunities);
  const rows = [...missing, ...applies];
  const codes = familyMissingCodes(detail);
  const noField = (code: string) => fieldForMissingCode(code) === null;
  const guideRows = rows.filter((row) => row.missingCodes.length > 0 && row.missingCodes.every(noField) && row.questions.length > 0);
  const covered = new Set(guideRows.flatMap((row) => row.missingCodes));
  return uniqueTexts([
    ...guideRows.flatMap((row) => row.questions),
    ...missingCodeLabels(codes.filter((code) => noField(code) && !covered.has(code))),
  ]);
}

/** Campos sobre los niños o niñas: la pista recuerda la composición; el resto, tramo RSH y urgencia. */
const CHILD_FIELDS: ReadonlySet<AddInfoQuestionKey> = new Set<AddInfoQuestionKey>([
  'child_age',
  'siblings_under_6',
  'siblings_6_14',
  'siblings_15_18',
  'chile_crece_contigo_access',
  'last_child_health_control_date',
  'child_possible_disability',
  'child_in_therapy',
  'pregnancy_public_network_delivery',
  'age_record_current',
]);

/** Hechos de la ficha relevantes al campo (composición, o tramo RSH + una señal de urgencia), en una línea. */
function familyFacts(key: AddInfoQuestionKey, detail: FamilyDetail, context: FamilyContextView | null): string {
  const facts: string[] = [];
  const children = detail.composition.filter((member) => member.role === 'CHILD');
  if (CHILD_FIELDS.has(key) && children.length > 0) {
    const youngest = Math.min(...children.map((member) => member.age));
    const age = youngest === 0 ? ADD_INFO_COPY.hintUnderOneYear : yearsLabel(youngest, formatInteger(youngest));
    facts.push(children.length === 1 ? ADD_INFO_COPY.hintChildOne(age) : ADD_INFO_COPY.hintChildren(formatInteger(children.length), age));
    return ADD_INFO_COPY.hintFamily(facts.join(', '));
  }
  facts.push(detail.rsh_band === null ? ADD_INFO_COPY.hintNoRshBand : ADD_INFO_COPY.hintRshBand(formatInteger(detail.rsh_band)));
  const signals = context?.urgency_signals;
  if (signals !== undefined) {
    const signal = (['recent_emergency', 'precarious_housing', 'limited_quota'] as const).find((key) => signals[key] === true);
    if (signal !== undefined) facts.push(ADD_INFO_COPY.hintSignal[signal]);
  }
  return ADD_INFO_COPY.hintFamily(facts.join(', '));
}

interface FieldImpact {
  readonly indet: Set<string>;
  readonly pending: Set<string>;
  /** Filas en orden del motor (rango = índice en "Falta información"). */
  readonly rows: Map<string, { row: BenefitRow; rank: number }>;
  bestRank: number;
}

const emptyImpact = (): FieldImpact => ({ indet: new Set(), pending: new Set(), rows: new Map(), bestRank: Number.POSITIVE_INFINITY });

function addRow(impact: FieldImpact, row: BenefitRow, rank: number) {
  if (row.result === 'INDETERMINADO') impact.indet.add(row.benefitId);
  else impact.pending.add(row.benefitId);
  if (!impact.rows.has(row.benefitId)) impact.rows.set(row.benefitId, { row, rank });
  impact.bestRank = Math.min(impact.bestRank, rank);
}

function mergeInto(target: FieldImpact, source: FieldImpact) {
  for (const { row, rank } of source.rows.values()) addRow(target, row, rank);
}

export function planQuestions({
  detail,
  opportunities,
  declared,
  context = null,
}: {
  readonly detail: FamilyDetail;
  readonly opportunities: readonly Opportunity[];
  readonly declared: ReadonlySet<AddInfoField>;
  readonly context?: FamilyContextView | null;
}): QuestionPlan {
  const rows = benefitSections(detail, opportunities).missing;
  const impacts = new Map<AddInfoQuestionKey, FieldImpact>();
  rows.forEach((row, rank) => {
    for (const code of row.missingCodes) {
      const field = fieldForMissingCode(code);
      if (field === null) continue;
      const impact = impacts.get(field) ?? emptyImpact();
      addRow(impact, row, rank);
      impacts.set(field, impact);
    }
  });

  // Ya declarado: no se vuelve a preguntar. Excepción: si el padre se declaró y el hijo no (semanas),
  // y el código del padre sigue faltando, el hijo se pregunta solo con el impacto del padre.
  for (const field of [...impacts.keys()]) {
    if (!declared.has(field)) continue;
    const impact = impacts.get(field) as FieldImpact;
    impacts.delete(field);
    for (const child of DEPENDENT_FIELDS[field] ?? []) {
      if (!declared.has(child)) impacts.set(child, impact);
    }
  }

  // Dependientes: van pegados a su padre y su impacto se suma al del padre.
  const dependents = new Map<AddInfoQuestionKey, AddInfoQuestionKey[]>();
  const attach = (parent: AddInfoQuestionKey, child: AddInfoQuestionKey) => {
    const parentImpact = impacts.get(parent);
    if (parentImpact === undefined || declared.has(child)) return;
    const childImpact = impacts.get(child);
    if (childImpact !== undefined) {
      mergeInto(parentImpact, childImpact);
      impacts.delete(child);
    }
    const list = dependents.get(parent) ?? [];
    if (!list.includes(child)) list.push(child);
    dependents.set(parent, list);
  };
  for (const parent of [...impacts.keys()]) for (const child of DEPENDENT_FIELDS[parent] ?? []) attach(parent, child);
  if (impacts.has('rsh_band')) attach('has_rsh', 'rsh_band');

  const shownHints = new Set<string>();
  const order = (key: AddInfoQuestionKey) => QUESTION_ORDER.indexOf(key);
  const planned = [...impacts.entries()]
    .sort(
      ([keyA, a], [keyB, b]) =>
        b.indet.size - a.indet.size || b.pending.size - a.pending.size || a.bestRank - b.bestRank || order(keyA) - order(keyB),
    )
    .map(([key, impact]): PlannedQuestion => {
      const byRank = [...impact.rows.values()].sort((a, b) => a.rank - b.rank).map(({ row }) => row);
      const names = (filter: (row: BenefitRow) => boolean) => [...new Set(byRank.filter(filter).map(readableBenefitName))];
      const top = byRank[0];
      const topName = top === undefined ? ADD_INFO_COPY.otherBenefit : readableBenefitName(top);
      const state = top?.result === 'INDETERMINADO' ? ADD_INFO_COPY.hintStateUnknown(topName) : ADD_INFO_COPY.hintStatePending(topName);
      // Una pista idéntica a la de una pregunta anterior no se repite (null).
      const text = `${familyFacts(key, detail, context)} ${state}`;
      const hint = shownHints.has(text) ? null : text;
      shownHints.add(text);
      return {
        key,
        dependents: (dependents.get(key) ?? []).sort((a, b) => order(a) - order(b)),
        opens: names((row) => row.result === 'INDETERMINADO'),
        completes: names((row) => row.result !== 'INDETERMINADO'),
        hint,
      };
    });

  return {
    primary: planned.slice(0, MAX_PRIMARY_QUESTIONS),
    more: planned.slice(MAX_PRIMARY_QUESTIONS),
    pendingBenefits: rows.length,
    guide: guideFor(detail, opportunities),
  };
}

/** Todos los campos planificados (principales, "ver más" y dependientes), en orden de pantalla. */
export function plannedFields(plan: QuestionPlan): AddInfoQuestionKey[] {
  return [...plan.primary, ...plan.more].flatMap((question) => [question.key, ...question.dependents]);
}

export interface ChangedBenefit {
  readonly name: string;
  /** Media frase de por qué (lo declarado que lo destrabó, o lo que aún falta); null si no hay. */
  readonly reason: string | null;
}

export interface AfterSaveDiff {
  readonly nowApplies: readonly ChangedBenefit[];
  readonly stillMissing: readonly ChangedBenefit[];
  readonly notListed: readonly ChangedBenefit[];
}

const MAX_REASON_ITEMS = 3;

/** Etiqueta corta de un campo (para el resultado); semanas con el umbral N. */
function shortFieldLabel(field: AddInfoField, weeks: number | null): string | null {
  if (field === 'pregnancy_weeks_at_least_threshold') {
    return weeks === null ? ADD_INFO_COPY.weeksShortMin : ADD_INFO_COPY.weeksShortN(formatInteger(weeks));
  }
  const labels: Readonly<Partial<Record<AddInfoField, string>>> = ADD_INFO_COPY.fieldShort;
  return labels[field] ?? null;
}

/** Campos de una fila previa (con dependientes) que la tía respondió en este envío. */
function answeredFor(row: BenefitRow, answered: ReadonlyMap<AddInfoField, string>, weeks: number | null): string | null {
  const fields = new Set<AddInfoField>();
  for (const code of row.missingCodes) {
    const field = fieldForMissingCode(code);
    if (field === null) continue;
    fields.add(field);
    for (const child of DEPENDENT_FIELDS[field] ?? []) fields.add(child);
    if (field === 'has_rsh') fields.add('rsh_band');
  }
  const items = QUESTION_ORDER.filter((field) => fields.has(field) && answered.has(field))
    .map((field) => {
      const label = shortFieldLabel(field, weeks);
      return label === null ? null : `${label}: ${answered.get(field) ?? ''}`;
    })
    .filter((item): item is string => item !== null)
    .slice(0, MAX_REASON_ITEMS);
  return items.length === 0 ? null : ADD_INFO_COPY.becauseDeclared(items.join('; '));
}

/**
 * Antes/después según el recálculo del motor: cada fila que estaba en "Falta información" queda en
 * "Ahora aplica", "Sigue faltando" o ya no aparece. `answered` = campo → texto de la respuesta.
 */
export function diffAfterSave(
  beforeRows: readonly BenefitRow[],
  after: FamilyDetail,
  opportunities: readonly Opportunity[],
  answered: ReadonlyMap<AddInfoField, string>,
  weeks: number | null,
): AfterSaveDiff {
  const sections = benefitSections(after, opportunities);
  const find = (id: string, section: readonly BenefitRow[]) => section.find((row) => row.benefitId === id);
  const nowApplies: ChangedBenefit[] = [];
  const stillMissing: ChangedBenefit[] = [];
  const notListed: ChangedBenefit[] = [];
  for (const before of beforeRows) {
    const name = readableBenefitName(before);
    const applied = find(before.benefitId, sections.apply);
    const missing = find(before.benefitId, sections.missing);
    if (applied !== undefined) {
      nowApplies.push({ name, reason: answeredFor(before, answered, weeks) });
    } else if (missing !== undefined) {
      // Solo los apoyos a los que se les respondió algo en este envío (el resto no cambió).
      if (answeredFor(before, answered, weeks) === null) continue;
      const labels = knownMissingLabels(missing.missingCodes).slice(0, MAX_REASON_ITEMS);
      stillMissing.push({ name, reason: labels.length === 0 ? null : ADD_INFO_COPY.becauseMissing(labels.join(', ')) });
    } else {
      notListed.push({ name, reason: null });
    }
  }
  return { nowApplies, stillMissing, notListed };
}
