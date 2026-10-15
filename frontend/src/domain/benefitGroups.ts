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
}

export interface BenefitGroups {
  /** result SI (salvo PENDIENTE_ANTECEDENTES). */
  readonly applies: readonly BenefitRow[];
  /** result INDETERMINADO o access_state PENDIENTE_ANTECEDENTES. */
  readonly missing: readonly BenefitRow[];
}

/**
 * `extra` = Opportunities adicionales de C3 (p. ej. listOportunidades `prioridad`), solo para
 * completar `simple_title` y preguntas sugeridas por igualdad de `benefit_id`.
 */
export function groupBenefits(detail: FamilyDetail, extra: readonly Opportunity[] = []): BenefitGroups {
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
      questions: [...new Set(opportunity?.suggested_questions ?? [])],
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
      questions: [...new Set(opportunity.suggested_questions)],
    });
  }

  const isMissing = (row: BenefitRow) => row.result === 'INDETERMINADO' || row.accessState === 'PENDIENTE_ANTECEDENTES';
  return {
    applies: rows.filter((row) => row.result === 'SI' && !isMissing(row)),
    missing: rows.filter(isMissing),
  };
}

/** Códigos faltantes de los beneficios de la familia, sin duplicados, en orden de aparición. */
export function familyMissingCodes(detail: FamilyDetail): string[] {
  const codes = [...detail.benefit_results.flatMap((r) => r.missing_codes), ...detail.top_opportunities.flatMap((o) => o.missing_codes)];
  return [...new Set(codes)];
}
