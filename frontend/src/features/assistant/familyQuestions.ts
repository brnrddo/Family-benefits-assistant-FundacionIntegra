// "Preguntas tipo" por familia (plan de arreglos §7): respuestas deterministas armadas con lo que ya
// trae `GET /familias/{id}/oportunidades` (orden del motor, action_type, where_to_go, why_first,
// missing_codes, suggested_questions). El motor decide qué y en qué orden; aquí solo se redacta.
import type { Opportunity } from '../../api/types';
import { benefitName } from '../../i18n/copy';
import { familyRef } from '../demo-session/demoCopy';
import { benefitStatus } from './familyHint';

export type QuickQuestionId = 'first' | 'missing' | 'pending';
export interface QuickQuestion {
  readonly id: QuickQuestionId;
  readonly question: string;
  readonly lines: readonly string[];
}

const MAX_BENEFITS = 3;
const PENDING_STATES = new Set<Opportunity['access_state']>(['SIN_CUPO', 'GESTION_EN_CURSO', 'GESTION_RECHAZADA']);

function actionLine(o: Opportunity): string {
  const name = benefitName(o.benefit_id, o.simple_title);
  switch (o.action_type) {
    case 'FAMILY_ACTION':
      return o.where_to_go ? `Presénteles ${name}. Dónde: ${o.where_to_go}.` : `Presénteles ${name}.`;
    case 'ASK_FIRST': {
      const ask = o.suggested_questions[0];
      return ask !== undefined ? `${name}: pregúnteles «${ask}»` : `${name}: pregúnteles primero si ya lo conocen.`;
    }
    case 'FOLLOW_UP':
      return `Haga seguimiento de ${name}.`;
    case 'AUTOMATIC':
      return `${name} se asigna solo: confirme que lo reciben.`;
  }
}

/**
 * Hasta 3 preguntas tipo; cada una con hasta 3 líneas concretas. Vacío si no hay nada pendiente.
 * `reminder` (familyHint.ts, solo pantalla) recuerda el hogar y el tramo antes de las acciones.
 */
export function buildQuickQuestions(
  opportunities: readonly Opportunity[],
  childName: string | null,
  reminder: string | null = null,
): QuickQuestion[] {
  const open = opportunities.filter((o) => o.access_state !== 'ASIGNADO');
  const out: QuickQuestion[] = [];
  const top = open.slice(0, MAX_BENEFITS);
  if (top.length > 0) {
    out.push({
      id: 'first',
      question: `¿Qué le presento primero a ${familyRef(childName)}?`,
      lines: [
        ...(reminder !== null ? [reminder] : []),
        // Cada acción con su porqué: el estado que entrega C3 y su `why_first`.
        ...top.map((o) => [actionLine(o), `Por qué: ${benefitStatus(o)}.`, o.why_first].filter((part) => part !== '').join(' ')),
      ],
    });
  }
  const asks = [...new Set(open.filter((o) => o.missing_codes.length > 0).flatMap((o) => o.suggested_questions))].slice(0, MAX_BENEFITS);
  if (asks.length > 0) out.push({ id: 'missing', question: '¿Qué me falta preguntarle?', lines: asks });
  const pending = open.filter((o) => PENDING_STATES.has(o.access_state) || o.action_type === 'FOLLOW_UP').slice(0, MAX_BENEFITS);
  if (pending.length > 0) {
    out.push({
      id: 'pending',
      question: '¿Qué hago con lo pendiente?',
      lines: pending.map((o) => {
        const name = benefitName(o.benefit_id, o.simple_title);
        return o.access_state === 'SIN_CUPO'
          ? `${name}: por ahora no hay cupo. Consulte en la institución qué opciones hay.`
          : `Haga seguimiento de ${name} y anote la respuesta de la institución.`;
      }),
    });
  }
  return out;
}
