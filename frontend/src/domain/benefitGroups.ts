// Agrupación de PRESENTACIÓN de los beneficios de una ficha (cambio 3, DEC-037). Usa los
// `benefit_results`/`top_opportunities` de C3 TAL COMO VIENEN: solo los separa por enums que ya
// entrega C3 (result/access_state) y no infiere elegibilidad, no reordena ni filtra por puntaje
// (FE-003). La ficha ya no trae NO/NO_APLICA (DEC-070, solo lo relevante); si llegaran, aquí no se
// muestran. El detalle técnico de cada tarjeta solo muestra su propio resultado (siempre SI/IND).
import type { AccessState, BenefitResultValue, FamilyDetail, Level, Opportunity } from '../api/types';

export interface BenefitRow {
  readonly benefitId: string;
  /** `simple_title` de C3 si hay una Opportunity del mismo beneficio; si no, null. */
  readonly simpleTitle: string | null;
  readonly result: BenefitResultValue;
  readonly level: Level | null;
  readonly accessState: AccessState;
  readonly missingCodes: readonly string[];
  /** `suggested_questions` de C3 del mismo beneficio (sin duplicados). */
  readonly questions: readonly string[];
  /** Opportunity de C3 del mismo beneficio (dónde ir, fuentes); null si no hay. */
  readonly opportunity: Opportunity | null;
}

export interface BenefitGroups {
  /** result SI (salvo PENDIENTE_ANTECEDENTES con códigos). */
  readonly applies: readonly BenefitRow[];
  /** result INDETERMINADO o access_state PENDIENTE_ANTECEDENTES con códigos. */
  readonly missing: readonly BenefitRow[];
}

/** Filas de presentación: `benefit_results` en su orden, más las del top que no vengan ahí. */
function benefitRows(detail: FamilyDetail, extra: readonly Opportunity[]): BenefitRow[] {
  const byId = new Map<string, Opportunity>();
  for (const opportunity of [...extra, ...detail.top_opportunities]) byId.set(opportunity.benefit_id, opportunity);

  const rows: BenefitRow[] = detail.benefit_results.map((result) => {
    const opportunity = byId.get(result.benefit_id);
    return {
      benefitId: result.benefit_id,
      simpleTitle: opportunity?.simple_title ?? null,
      result: result.result,
      level: result.level,
      accessState: result.access_state,
      missingCodes: result.missing_codes,
      questions: uniqueTexts(opportunity?.suggested_questions ?? []),
      opportunity: opportunity ?? null,
    };
  });
  // Una oportunidad del top que no venga en benefit_results se muestra igual (sin reinterpretarla).
  const known = new Set(rows.map((row) => row.benefitId));
  for (const opportunity of detail.top_opportunities) {
    if (known.has(opportunity.benefit_id)) continue;
    rows.push({
      benefitId: opportunity.benefit_id,
      simpleTitle: opportunity.simple_title,
      result: opportunity.result,
      level: opportunity.level,
      accessState: opportunity.access_state,
      missingCodes: opportunity.missing_codes,
      questions: uniqueTexts(opportunity.suggested_questions),
      opportunity,
    });
  }
  return rows;
}

/**
 * `extra` = Opportunities adicionales de C3 (p. ej. listOportunidades `prioridad`), solo para
 * completar `simple_title` y preguntas sugeridas por igualdad de `benefit_id`.
 */
export function groupBenefits(detail: FamilyDetail, extra: readonly Opportunity[] = []): BenefitGroups {
  const rows = benefitRows(detail, extra);
  const isMissing = (row: BenefitRow) =>
    !isPendingWithoutCodes(row) && (row.result === 'INDETERMINADO' || row.accessState === 'PENDIENTE_ANTECEDENTES');
  return {
    applies: rows.filter((row) => row.result === 'SI' && !isMissing(row)),
    missing: rows.filter(isMissing),
  };
}

// --- Secciones de la ficha (Puede postular / Falta información / Ya postuló o sin cupo) ---
// Orden: el de C3 `listOportunidades?orden=prioridad` (U/B/V del motor, DEC-053); mientras carga,
// `detail.top_opportunities`. Las filas sin Opportunity van al final en su orden de `benefit_results`.
// El cliente no ordena por puntaje (FE-003): solo aplica la posición que ya entrega C3.

export type BenefitSection = 'apply' | 'missing' | 'done';
export type BenefitFilter = 'all' | BenefitSection;
export const SECTION_ORDER: readonly BenefitSection[] = ['apply', 'missing', 'done'];
export type BenefitSections = Readonly<Record<BenefitSection, readonly BenefitRow[]>>;

const DONE_STATES: ReadonlySet<AccessState> = new Set(['ASIGNADO', 'GESTION_EN_CURSO', 'GESTION_RECHAZADA', 'SIN_CUPO']);

/**
 * SI PENDIENTE_ANTECEDENTES sin `missing_codes`: la base no dice qué falta (supuestos del motor), así
 * que no se pide nada (decisión del usuario, diagnostico-faltantes.md) y va a "Puede postular ahora".
 * Con códigos reales sigue en "Falta información".
 */
export function isPendingWithoutCodes(row: BenefitRow): boolean {
  return row.result === 'SI' && row.accessState === 'PENDIENTE_ANTECEDENTES' && row.missingCodes.length === 0;
}

/** Sección por enums de C3; null = no se muestra (NO/NO_APLICA). */
export function sectionOf(row: BenefitRow): BenefitSection | null {
  if (isPendingWithoutCodes(row)) return 'apply';
  if (row.result === 'INDETERMINADO' || row.accessState === 'PENDIENTE_ANTECEDENTES') return 'missing';
  if (row.result === 'SI' && row.accessState === 'ELEGIBLE_SIN_ASIGNACION') return 'apply';
  if (DONE_STATES.has(row.accessState)) return 'done';
  return null;
}

export function benefitSections(detail: FamilyDetail, prioridad: readonly Opportunity[]): BenefitSections {
  const ranking = prioridad.length > 0 ? prioridad : detail.top_opportunities;
  const rank = new Map(ranking.map((opportunity, index) => [opportunity.benefit_id, index]));
  const rows = benefitRows(detail, prioridad)
    .map((row, index) => ({ row, key: rank.get(row.benefitId) ?? ranking.length + index }))
    .sort((a, b) => a.key - b.key)
    .map(({ row }) => row);
  const out: Record<BenefitSection, BenefitRow[]> = { apply: [], missing: [], done: [] };
  for (const row of rows) {
    const section = sectionOf(row);
    if (section !== null) out[section].push(row);
  }
  return out;
}

/** Con "Todos": las secciones con filas; con un filtro: solo esa. */
export function visibleSections(sections: BenefitSections, filter: BenefitFilter): BenefitSection[] {
  if (filter !== 'all') return [filter];
  return SECTION_ORDER.filter((section) => sections[section].length > 0);
}

/** Forma de comparación: sin espacios de más, minúsculas y sin ¿?¡!. en los bordes. */
function normalizedText(text: string): string {
  return text
    .trim()
    .replace(/\s+/g, ' ')
    .toLocaleLowerCase('es')
    .replace(/^[¿?¡!.\s]+|[¿?¡!.\s]+$/g, '');
}

/** Textos sin repetidos (misma pregunta con otra puntuación o mayúsculas); conserva el primero tal cual. */
export function uniqueTexts(texts: readonly string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const text of texts) {
    const key = normalizedText(text);
    if (key === '' || seen.has(key)) continue;
    seen.add(key);
    out.push(text);
  }
  return out;
}

/** Códigos faltantes de los beneficios de la familia, sin duplicados, en orden de aparición. */
export function familyMissingCodes(detail: FamilyDetail): string[] {
  const codes = [...detail.benefit_results.flatMap((r) => r.missing_codes), ...detail.top_opportunities.flatMap((o) => o.missing_codes)];
  return [...new Set(codes)];
}
