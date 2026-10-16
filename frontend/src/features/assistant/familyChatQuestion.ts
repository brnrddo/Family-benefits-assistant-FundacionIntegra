// Pregunta del chat de la ficha (guion de demo 2026-10-16). C3 `POST /asistente` solo acepta
// `{ question }` (≤500 code points), así que el contexto viaja dentro de la misma cadena:
// "Contexto de la familia: <roles y edades>, tramo RSH <n>, beneficios en la ficha: <hasta 3 títulos
// (aplica|falta dato)>. Situación que cuenta la tía: <texto>". Solo datos permitidos (LlmContextV1:
// roles/edades, tramo RSH, títulos y estado); nunca nombres ni IDs de familia o niño. Si no cabe, se
// recorta primero el contexto: el texto de la tía se conserva entero. Puro: sin red ni logs.
import type { CompositionMember, Opportunity } from '../../api/types';
import { benefitName } from '../../i18n/copy';
import { FAMILY_CONTEXT_COPY as C } from '../demo-session/demoCopy';

export const FAMILY_QUESTION_MAX = 500;
/** Tope del texto de la tía: siempre cabe junto al prefijo y la marca de situación. */
export const TIA_TEXT_MAX = 300;
const MAX_BENEFITS = 3;

const codePoints = (text: string): number => [...text].length;
const years = (age: number): string => (age === 1 ? '1 año' : `${age} años`);
/** Sin ';', llaves, '<>' ni URLs: el backend los trata como markup y los títulos C3 no los traen. */
const plain = (text: string): string => text.replace(/[;{}<>]/g, ' ').replace(/https?:\/\/\S+/gi, ' ').replace(/\s+/g, ' ').trim();

export interface FamilyQuestionInput {
  readonly composition: readonly CompositionMember[];
  readonly rshBand: number | null;
  readonly opportunities: readonly Opportunity[];
  /** Texto de la tía YA sin nombres locales (`replaceLocalNames`). */
  readonly tiaText: string;
}

export function composeFamilyQuestion({ composition, rshBand, opportunities, tiaText }: FamilyQuestionInput): string {
  const tia = [...plain(tiaText)].slice(0, TIA_TEXT_MAX).join('');
  const members = composition.map((m) => `${C.roles[m.role]} de ${years(m.age)}`);
  const rsh = rshBand === null ? C.rshNone : `${C.rsh} ${rshBand}`;
  let benefits = opportunities
    .filter((o) => o.result === 'SI' || o.result === 'INDETERMINADO')
    .slice(0, MAX_BENEFITS)
    .map((o) => `${plain(benefitName(o.benefit_id, o.simple_title))} (${o.result === 'SI' ? C.applies : C.missing})`);
  const tail = ` ${C.situation} ${tia}`;
  const build = (): string => {
    const parts = [...members, rsh, ...(benefits.length > 0 ? [`${C.benefits} ${benefits.join(', ')}`] : [])];
    return `${C.prefix} ${parts.join(', ')}.`;
  };
  // Recorte del contexto: primero beneficios del final, luego caracteres con "…".
  let context = build();
  while (codePoints(context) + codePoints(tail) > FAMILY_QUESTION_MAX && benefits.length > 0) {
    benefits = benefits.slice(0, -1);
    context = build();
  }
  const room = FAMILY_QUESTION_MAX - codePoints(tail);
  if (codePoints(context) > room) context = `${[...context].slice(0, room - 1).join('')}…`;
  return `${context}${tail}`;
}
