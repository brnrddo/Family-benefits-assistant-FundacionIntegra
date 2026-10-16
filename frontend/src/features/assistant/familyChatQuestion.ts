// Pregunta del chat de la ficha (guion de demo 2026-10-16). C3 `POST /asistente` solo acepta
// `{ question }` (≤500 code points), así que el contexto viaja dentro de la misma cadena:
// "Contexto de la familia: <roles y edades>, tramo RSH <n>, beneficios en la ficha: <hasta 3 títulos
// (aplica|falta dato)>. [Antes hablamos de: <resumen>.] Situación que cuenta la tía: <texto>". Solo
// datos permitidos (LlmContextV1: roles/edades, tramo RSH, títulos y estado); nunca nombres ni IDs de
// familia o niño. Si no cabe, se recorta primero el turno previo, luego el contexto: el texto de la tía
// se conserva entero. Puro: sin red ni logs.
import type { CompositionMember, Opportunity } from '../../api/types';
import { benefitName } from '../../i18n/copy';
import { FAMILY_CONTEXT_COPY as C } from '../demo-session/demoCopy';
import { codePoints, plainText as plain, previousSegment, QUESTION_MAX } from './chatContext';

export const FAMILY_QUESTION_MAX = QUESTION_MAX;
/** Tope de lo que escribe la tía (textarea); tras reemplazar nombres puede crecer y se recorta el contexto. */
export const TIA_TEXT_MAX = 300;
const MAX_BENEFITS = 3;

const years = (age: number): string => (age === 1 ? '1 año' : `${age} años`);

export interface FamilyQuestionInput {
  readonly composition: readonly CompositionMember[];
  readonly rshBand: number | null;
  readonly opportunities: readonly Opportunity[];
  /** Texto de la tía YA sin nombres locales (`replaceLocalNames`). */
  readonly tiaText: string;
  /** Última respuesta del asistente en este hilo, YA sin nombres locales (null si no hay). */
  readonly previousAnswer?: string | null;
  /** Pista determinista SIN nombres (familyHint.ts): el porqué del primer apoyo. */
  readonly hint?: string | null;
}

/**
 * Tope del texto de la tía YA reemplazado: puede pasar de TIA_TEXT_MAX ("Juanito" → "el niño o la
 * niña"), así que solo se corta cuando el contexto ya quedó reducido a "<prefijo> …".
 */
const TIA_HARD_MAX = FAMILY_QUESTION_MAX - codePoints(`${C.prefix} …`) - codePoints(`  ${C.situation}`);

export function composeFamilyQuestion({
  composition,
  rshBand,
  opportunities,
  tiaText,
  previousAnswer = null,
  hint = null,
}: FamilyQuestionInput): string {
  const tia = [...plain(tiaText)].slice(0, TIA_HARD_MAX).join('');
  const members = composition.map((m) => `${C.roles[m.role]} de ${years(m.age)}`);
  const rsh = rshBand === null ? C.rshNone : `${C.rsh} ${rshBand}`;
  let benefits = opportunities
    .filter((o) => o.result === 'SI' || o.result === 'INDETERMINADO')
    .slice(0, MAX_BENEFITS)
    .map((o) => `${plain(benefitName(o.benefit_id, o.simple_title))} (${o.result === 'SI' ? C.applies : C.missing})`);
  const tail = ` ${C.situation} ${tia}`;
  const cleanHint = hint === null ? '' : plain(hint);
  let withHint = cleanHint !== '';
  const build = (): string => {
    const parts = [...members, rsh, ...(benefits.length > 0 ? [`${C.benefits} ${benefits.join(', ')}`] : [])];
    return `${C.prefix} ${parts.join(', ')}.${withHint ? ` ${C.hint} ${cleanHint}` : ''}`;
  };
  let context = build();
  // 1) Turno previo: solo con el espacio que dejan el contexto completo y el texto de la tía.
  const previous = previousSegment(previousAnswer, FAMILY_QUESTION_MAX - codePoints(context) - codePoints(tail) - 1);
  if (previous !== '') return `${context} ${previous}${tail}`;
  // 2) Contexto: primero la pista, luego beneficios del final y al final caracteres con "…".
  if (withHint && codePoints(context) + codePoints(tail) > FAMILY_QUESTION_MAX) {
    withHint = false;
    context = build();
  }
  while (codePoints(context) + codePoints(tail) > FAMILY_QUESTION_MAX && benefits.length > 0) {
    benefits = benefits.slice(0, -1);
    context = build();
  }
  const room = FAMILY_QUESTION_MAX - codePoints(tail);
  if (codePoints(context) > room) context = `${[...context].slice(0, room - 1).join('')}…`;
  return `${context}${tail}`;
}
