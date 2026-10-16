// Preguntas del jardín en el chat (plan de arreglos, decisión 9): plantilla determinista desde los
// `top_gaps` de `GET /kpi` del jardín, en el frontend. Sin LLM y sin llamar a /asistente (su request es
// solo `{question}`). Las cifras van tal cual vienen de C3.
import type { KpiResult } from '../../api/types';
import { formatInteger } from '../../domain/format';
import { benefitLabel } from '../../i18n/copy';
import { DEMO_COPY, familiesCount, type GardenQuestionKind } from '../demo-session/demoCopy';

type Gap = KpiResult['top_gaps'][number];

const joinNames = (names: readonly string[]): string =>
  names.length <= 1 ? (names[0] ?? '') : `${names.slice(0, -1).join(', ')} y ${names[names.length - 1] ?? ''}`;

export function gardenAnswer(kind: GardenQuestionKind, kpi: KpiResult | undefined): string {
  if (kpi === undefined || kpi.suppressed || kpi.top_gaps.length === 0) return DEMO_COPY.chatGardenNoData;
  const gaps: readonly Gap[] = [...kpi.top_gaps].sort((a, b) => b.family_count - a.family_count).slice(0, 3);
  const [first, ...rest] = gaps;
  if (first === undefined) return DEMO_COPY.chatGardenNoData;
  const firstName = benefitLabel(first.benefit_id);
  const firstCount = familiesCount(formatInteger(first.family_count));
  if (kind === 'meeting') {
    const after = rest.length > 0 ? ` Después: ${joinNames(rest.map((g) => benefitLabel(g.benefit_id)))}.` : '';
    return `Para la reunión, el tema con más familias cerca de acceder es ${firstName} (${firstCount}).${after} Lleve la información de dónde se consulta cada uno.`;
  }
  const after =
    rest.length > 0
      ? ` Le siguen ${joinNames(rest.map((g) => `${benefitLabel(g.benefit_id)} (${familiesCount(formatInteger(g.family_count))})`))}.`
      : '';
  return `El apoyo que más se repite en su jardín es ${firstName}: ${firstCount} lo tienen pendiente.${after}`;
}
