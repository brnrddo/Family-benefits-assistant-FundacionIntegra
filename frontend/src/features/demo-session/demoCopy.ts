// Copy de la sesión demo, Inicio y chat (plan de arreglos, decisión 1: sin claves i18n nuevas para no
// recalcular el bundle C4). Texto plano en español, sin HTML. Rol 4 lo revisa y se migra a es.json
// cuando se recalcule el bundle. Nunca promete resultados: el motor decide, el texto solo orienta.
import { APP_NAME } from '../../brand';
export const DEMO_COPY = {
  gateTitle: `Bienvenida a ${APP_NAME}`,
  gateIntro: 'Entre a la demo como la educadora del jardín. Verá a sus familias, sus avances y el chat de situaciones.',
  gateFictionNotice: 'Demo: personas, jardines y beneficios son ficticios.',
  gateGardenLabel: 'Jardín',
  homeChatCta: 'Cuénteme una situación y le muestro apoyos',
  statsTitle: 'Su jardín hoy',
  statsFamilies: 'familias',
  statsInformed: 'informadas',
  statsOpportunities: 'apoyos por activar',
  statsTopTitle: 'Lo que más se repite',
  searchLabel: 'Buscar familia',
  searchHint: 'Escriba el nombre del niño o niña, el apellido o el número.',
  searchEmpty: 'No encontramos familias con esa búsqueda.',
  chatTitle: 'Cuénteme una situación',
  chatIntro: 'Cuénteme qué está pasando con una familia y le muestro qué apoyos del catálogo puede presentarles.',
  chatSituationsTitle: 'Situaciones',
  chatGardenTitle: 'Su jardín',
  chatYou: 'Usted',
  chatAssistant: APP_NAME,
  chatGardenNoData: 'Aún no tengo los datos de su jardín. Intente de nuevo en un momento.',
  chatHistoryLabel: 'Conversación',
  quickTitle: 'Preguntas rápidas',
  quickNoData: 'Por ahora no hay apoyos pendientes para esta familia.',
  // Acción del día y memoria local (DEC-091).
  todayTitle: 'Hoy',
  todayOpenFamily: 'Ver la familia',
  todayHideMore: 'Ocultar',
  todayAllDone: 'Por hoy está al día. Gracias por acompañar a sus familias.',
  statsOpen: 'Ver resumen del jardín',
  statsClose: 'Ocultar resumen',
  listClose: 'Ocultar familias',
  // Chat de la ficha (guion de demo 2026-10-16): trato de usted como el resto de la app.
  familyChatLabel: 'Cuénteme la situación de esta familia',
  familyChatHint: 'No hace falta escribir nombres: si los escribe, los cambio por «el niño o la niña».',
  familyChatSubmit: 'Pedir ideas',
  familyChatNameBlocked: 'No pude quitar un nombre guardado del texto. Escríbalo sin nombres.',
} as const;

/** Partes del contexto que el chat de la ficha antepone a la pregunta (solo datos permitidos). */
export const FAMILY_CONTEXT_COPY = {
  prefix: 'Contexto de la familia:',
  situation: 'Situación que cuenta la tía:',
  rsh: 'tramo RSH',
  rshNone: 'sin tramo RSH',
  benefits: 'beneficios en la ficha:',
  applies: 'aplica',
  missing: 'falta dato',
  roles: { ADULT_REFERENCE: 'adulto de referencia', CHILD: 'niño o niña', OTHER_ADULT: 'otro adulto' },
} as const;

const capitalize = (text: string): string => text.charAt(0).toLocaleUpperCase('es-CL') + text.slice(1);

/** "La familia de Antonella tiene 3 apoyos posibles y solo le faltan 2 datos." (singular y sin faltantes). */
export const todaySummaryLine = (who: string, possible: number, missing: number): string => {
  const head = `${capitalize(who)} tiene ${possible} ${possible === 1 ? 'apoyo posible' : 'apoyos posibles'}`;
  if (missing === 0) return `${head}.`;
  return `${head} y solo le ${missing === 1 ? 'falta 1 dato' : `faltan ${missing} datos`}.`;
};

/** Frase de la acción del día: "Converse con la familia de Antonella sobre" + nombre del apoyo. */
export const todayLead = (who: string): string => `Converse con ${who} sobre`;
export const todayMore = (n: number): string => `y ${n} más`;
export const listOpen = (n: number): string => `Ver todas las familias (${n})`;
/** Cuándo, en palabras: "hoy", "ayer", "hace 3 días". */
export const whenLabel = (daysAgo: number): string => (daysAgo <= 0 ? 'hoy' : daysAgo === 1 ? 'ayer' : `hace ${daysAgo} días`);
/** "Ayer habló con la familia de Juanito ✓" ("Hoy habló…", "Hace 3 días habló…"). */
export const doneLine = (who: string, when: string): string => `${capitalize(when)} habló con ${who} ✓`;
/** Saludo del chat con memoria: lo último que hizo la tía y la sugerencia de hoy (ambas opcionales). */
export const chatMemory = (
  last: { readonly who: string; readonly benefit: string | null; readonly when: string } | null,
  next: { readonly who: string; readonly benefit: string } | null,
): string | null => {
  const parts: string[] = [];
  if (last !== null) {
    parts.push(`La última vez habló con ${last.who}${last.benefit !== null ? ` sobre ${last.benefit}` : ''} (${last.when}).`);
  }
  if (next !== null) parts.push(`Hoy le sugiero conversar con ${next.who} sobre ${next.benefit}.`);
  else if (last !== null) parts.push('Por hoy está al día.');
  return parts.length > 0 ? parts.join(' ') : null;
};

/** Chips de situación: se envían tal cual al asistente (tabla cerrada del servidor). */
export const SITUATION_EXAMPLES: readonly string[] = [
  'La mamá está embarazada y se quedó sin trabajo',
  'Vive con su abuelo en la casa',
  'Les cortaron el agua',
  'El niño tiene una discapacidad',
];

export type GardenQuestionKind = 'meeting' | 'most_families';
export const GARDEN_EXAMPLES: readonly { readonly kind: GardenQuestionKind; readonly text: string }[] = [
  { kind: 'meeting', text: 'Tengo reunión de apoderados el jueves' },
  { kind: 'most_families', text: '¿Qué tema le sirve a más familias?' },
];

export const greeting = (tia: string): string => `Hola, ${tia}`;
export const gateEnter = (tia: string): string => `Entrar como ${tia} (demo)`;
export const headerLabel = (tia: string, garden: string): string => `${tia} · ${garden}`;
export const familiesCount = (n: string): string => `${n} ${n === '1' ? 'familia' : 'familias'}`;
export const familyRef = (child: string | null): string => (child === null ? 'esta familia' : `la familia de ${child}`);
