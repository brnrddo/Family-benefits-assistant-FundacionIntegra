// Piezas compartidas por los dos chats (AssistantPage y FamilyChat). Puro: sin red ni logs.
// - Nombres: en vez de bloquear, los nombres guardados en el equipo y los apellidos del directorio demo
//   se cambian por "el niño o la niña" / "la familia" ANTES de enviar (DEC-038: nunca salen). En
//   pantalla el historial muestra lo que escribió la tía, que vive solo en memoria.
// - Continuidad: un resumen corto de la última respuesta ("Antes hablamos de: …") viaja dentro de la
//   misma `question` de C3 (≤500 code points). Prioridad al recortar: texto actual de la tía >
//   contexto de la familia > turno previo.
// - Aviso: C3 sigue enviando `disclaimer` y el `answer` puede terminar con el literal; cada burbuja lo
//   recorta al mostrar y la vista lo muestra una sola vez al pie.
import type { AssistantEnvelope } from '../../api/types';
import { t } from '../../i18n/copy';
import { replaceLocalNames } from '../../offline/localNames';
import type { DemoFamilyEntry } from '../demo-session/session';

export const QUESTION_MAX = 500;
/** Largo máximo del resumen del turno anterior (code points). */
export const PREVIOUS_MAX = 120;
/** Por debajo de esto el resumen ya no aporta: se omite. */
const PREVIOUS_MIN = 20;
export const PREVIOUS_LABEL = 'Antes hablamos de:';
export const CURRENT_LABEL = 'Ahora la tía pregunta:';

export const codePoints = (text: string): number => [...text].length;
const slice = (text: string, max: number): string => [...text].slice(0, max).join('');

/** Sin ';', llaves, '<>' ni URLs: el backend los trata como markup y no aportan al resumen. */
export const plainText = (text: string): string =>
  text.replace(/[;{}<>]/g, ' ').replace(/https?:\/\/\S+/gi, ' ').replace(/\s+/g, ' ').trim();

/** Apellidos de TODO el directorio demo ("Familia Rojas Muñoz" → "Rojas Muñoz"). */
export const directoryFamilyWords = (directory: ReadonlyMap<string, DemoFamilyEntry>): string[] =>
  [...directory.values()].map((entry) => entry.familyName.replace(/^familia\s+/iu, ''));

/** Texto listo para salir: nombres guardados y apellidos del directorio reemplazados. */
export const anonymize = (text: string, names: ReadonlyMap<string, string>, directory: ReadonlyMap<string, DemoFamilyEntry>): string =>
  replaceLocalNames(text, names, directoryFamilyWords(directory));

/** Respuesta previa para dar continuidad (solo CATALOG_INFO del servidor; nunca derivación ni error). */
export function lastAnswerOf(turns: readonly { readonly kind: string; readonly envelope?: AssistantEnvelope }[]): string | null {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const turn = turns[i];
    if (turn?.kind === 'answer' && turn.envelope?.intent === 'CATALOG_INFO') return turn.envelope.answer;
  }
  return null;
}

/** El `answer` sin el aviso final (si lo trae): el aviso se muestra una sola vez en la vista. */
export function stripDisclaimer(answer: string): string {
  const notice = t('notice.referential');
  const trimmed = answer.trimEnd();
  return trimmed.endsWith(notice) ? trimmed.slice(0, trimmed.length - notice.length).trimEnd() : answer;
}

/** Resumen de la última respuesta: sin aviso, texto plano y a lo más `max` code points (con "…"). */
export function previousSummary(answer: string | null, max = PREVIOUS_MAX): string {
  if (answer === null || max < PREVIOUS_MIN) return '';
  // Sin dígitos ni correos: un teléfono de "dónde ir" no debe hacer que el servidor rechace la pregunta.
  const clean = plainText(stripDisclaimer(answer).replace(/\S*@\S*/g, ' ').replace(/\d+/g, ' '))
    .replace(/\s+([.,:])/g, '$1')
    .replace(/[.,:\s]+$/u, '');
  if (clean === '') return '';
  return codePoints(clean) <= max ? clean : `${slice(clean, max - 1).trimEnd()}…`;
}

/** Segmento "Antes hablamos de: <resumen>." que cabe en `room` code points ('' si no cabe). */
export function previousSegment(answer: string | null, room: number): string {
  const overhead = codePoints(`${PREVIOUS_LABEL} .`);
  const summary = previousSummary(answer, Math.min(PREVIOUS_MAX, room - overhead));
  return summary === '' ? '' : `${PREVIOUS_LABEL} ${summary}.`;
}

/**
 * Chat general: "Antes hablamos de: <resumen>. Ahora la tía pregunta: <texto>". Sin turno previo, el
 * texto tal cual. El texto de la tía nunca se recorta por el resumen: si no cabe, el resumen se omite.
 */
export function composeGeneralQuestion(text: string, previousAnswer: string | null): string {
  const current = slice(text.trim(), QUESTION_MAX);
  const room = QUESTION_MAX - codePoints(` ${CURRENT_LABEL} ${current}`);
  const previous = previousSegment(previousAnswer, room);
  return previous === '' ? current : `${previous} ${CURRENT_LABEL} ${current}`;
}
