// Textos derivados de la ficha (puro, sin React y sin LLM): faltantes concretos por beneficio, "Datos
// por confirmar" y el plan corto "Qué hacer ahora". Solo traduce enums/códigos de C3 y el orden que ya
// trae cada sección (FE-003); no decide elegibilidad. Bug C: un SI PENDIENTE_ANTECEDENTES sin códigos
// (supuestos del motor) muestra el documento a confirmar en vez del genérico "Un dato del hogar".
import type { CatalogScopeItem } from '../../api/proposals/types';
import type { FamilyContextView } from '../../api/types';
import { SECTION_ORDER, uniqueTexts, type BenefitRow, type BenefitSections } from '../../domain/benefitGroups';
import { INCONSISTENCY_KEY, knownMissingLabels } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { FAMILY_COPY } from './familyCopy';

export type Scopes = ReadonlyMap<string, CatalogScopeItem>;

const MAX_PLAN_ITEMS = 3;

/** Nombre: el de la propuesta solo para el ejemplo SOLO DEMO; si no, el de C3/copy como siempre. */
export function rowName(row: BenefitRow, scope: CatalogScopeItem | undefined): string {
  return scope?.demo === true ? scope.simple_title : benefitName(row.benefitId, row.simpleTitle);
}

/** "Falta saber" de una tarjeta: textos concretos; sin códigos con texto, el texto del estado. */
export function rowMissingTexts(row: BenefitRow): string[] {
  const labels = knownMissingLabels(row.missingCodes);
  if (labels.length > 0) return labels;
  return [row.accessState === 'PENDIENTE_ANTECEDENTES' ? FAMILY_COPY.pendingProofDetail : FAMILY_COPY.unknownDetail];
}

/** Texto por beneficio cuando la fila no trae códigos con texto (incluye el nombre). */
function rowFallback(row: BenefitRow, scopes: Scopes): string {
  return row.accessState === 'PENDIENTE_ANTECEDENTES' ? FAMILY_COPY.pendingProof(rowName(row, scopes.get(row.benefitId))) : FAMILY_COPY.unknownDetail;
}

/** "Datos por confirmar" de la tarjeta del hogar: contexto, inconsistencias y faltantes de las filas. */
export function toConfirmItems(sections: BenefitSections, context: FamilyContextView | null, scopes: Scopes): string[] {
  const rows = SECTION_ORDER.flatMap((section) => sections[section]);
  return uniqueTexts([
    ...knownMissingLabels(context?.missing_codes ?? []),
    ...(context?.inconsistency_codes ?? []).map((code) => t(INCONSISTENCY_KEY[code])),
    ...knownMissingLabels(rows.flatMap((row) => row.missingCodes)),
    ...sections.missing.filter((row) => knownMissingLabels(row.missingCodes).length === 0).map((row) => rowFallback(row, scopes)),
  ]);
}

export interface ActionPlan {
  /** Preguntas/datos concretos para la apoderada (máx. 3); null si no falta nada. */
  readonly ask: { readonly withForm: boolean; readonly items: readonly string[] } | null;
  /** Nombres de los primeros beneficios de "Puede postular ahora" (máx. 3). */
  readonly deliver: readonly string[];
  readonly none: boolean;
}

export function buildActionPlan(sections: BenefitSections, { canAddInfo, scopes }: { readonly canAddInfo: boolean; readonly scopes: Scopes }): ActionPlan {
  const asks = uniqueTexts(
    sections.missing.flatMap((row) => {
      if (row.questions.length > 0) return row.questions;
      const labels = knownMissingLabels(row.missingCodes);
      return labels.length > 0 ? labels : [rowFallback(row, scopes)];
    }),
  ).slice(0, MAX_PLAN_ITEMS);
  const ask = asks.length > 0 ? { withForm: canAddInfo, items: asks } : null;
  const deliver = sections.apply.slice(0, MAX_PLAN_ITEMS).map((row) => rowName(row, scopes.get(row.benefitId)));
  return { ask, deliver, none: ask === null && deliver.length === 0 };
}
