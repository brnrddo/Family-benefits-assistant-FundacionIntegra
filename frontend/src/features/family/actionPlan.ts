// Textos derivados de la ficha (puro, sin React y sin LLM): faltantes concretos por beneficio, "Datos
// por confirmar" y el plan corto "Qué hacer ahora". Solo traduce enums/códigos de C3 y el orden que ya
// trae cada sección (FE-003); no decide elegibilidad. Solo se usan los `missing_codes` que vienen en los
// datos: nunca se piden documentos que la base no registra (un SI pendiente sin códigos va a "Puede
// postular ahora", domain/benefitGroups.ts). Los datos sin pregunta Sí/No llevan el nombre del beneficio.
import { fieldForMissingCode } from '../../api/proposals/addInfo';
import type { CatalogScopeItem } from '../../api/proposals/types';
import type { FamilyContextView } from '../../api/types';
import { SECTION_ORDER, uniqueTexts, type BenefitRow, type BenefitSections } from '../../domain/benefitGroups';
import { INCONSISTENCY_KEY, knownMissingLabels } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { FAMILY_COPY } from './familyCopy';

export type Scopes = ReadonlyMap<string, CatalogScopeItem>;

const MAX_PLAN_ITEMS = 3;

const hasField = (code: string) => fieldForMissingCode(code) !== null;

/** Nombre: el de la propuesta solo para el ejemplo SOLO DEMO; si no, el de C3/copy como siempre. */
export function rowName(row: BenefitRow, scope: CatalogScopeItem | undefined): string {
  return scope?.demo === true ? scope.simple_title : benefitName(row.benefitId, row.simpleTitle);
}

/** "Falta saber" de una tarjeta: textos concretos; sin códigos con texto, el respaldo genérico de estado. */
export function rowMissingTexts(row: BenefitRow): string[] {
  const labels = knownMissingLabels(row.missingCodes);
  return labels.length > 0 ? labels : [FAMILY_COPY.unknownDetail];
}

/**
 * Datos de una fila fuera de la tarjeta: los que tienen pregunta Sí/No sueltos ("Semanas de embarazo")
 * y los que no (guías) en una línea con el nombre del beneficio.
 */
function rowConfirmTexts(row: BenefitRow, scopes: Scopes): string[] {
  const withField = knownMissingLabels(row.missingCodes.filter(hasField));
  const guides = knownMissingLabels(row.missingCodes.filter((code) => !hasField(code)));
  return guides.length > 0 ? [...withField, FAMILY_COPY.benefitGuide(rowName(row, scopes.get(row.benefitId)), guides)] : withField;
}

/** Filas de "Falta información" sin ningún código con texto: respaldo genérico (nunca un documento). */
function missingTexts(row: BenefitRow, scopes: Scopes): string[] {
  const texts = rowConfirmTexts(row, scopes);
  return texts.length > 0 ? texts : [FAMILY_COPY.unknownDetail];
}

/** "Datos por confirmar" de la tarjeta del hogar: contexto, inconsistencias y faltantes de las filas. */
export function toConfirmItems(sections: BenefitSections, context: FamilyContextView | null, scopes: Scopes): string[] {
  return uniqueTexts([
    ...knownMissingLabels(context?.missing_codes ?? []),
    ...(context?.inconsistency_codes ?? []).map((code) => t(INCONSISTENCY_KEY[code])),
    ...SECTION_ORDER.flatMap((section) =>
      sections[section].flatMap((row) => (section === 'missing' ? missingTexts(row, scopes) : rowConfirmTexts(row, scopes))),
    ),
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
    sections.missing.flatMap((row) => (row.questions.length > 0 ? row.questions : missingTexts(row, scopes))),
  ).slice(0, MAX_PLAN_ITEMS);
  // "Agregar información" solo si el formulario tiene al menos una pregunta Sí/No real.
  const hasQuestion = SECTION_ORDER.some((section) => sections[section].some((row) => row.missingCodes.some(hasField)));
  const ask = asks.length > 0 ? { withForm: canAddInfo && hasQuestion, items: asks } : null;
  const deliver = sections.apply.slice(0, MAX_PLAN_ITEMS).map((row) => rowName(row, scopes.get(row.benefitId)));
  return { ask, deliver, none: ask === null && deliver.length === 0 };
}
