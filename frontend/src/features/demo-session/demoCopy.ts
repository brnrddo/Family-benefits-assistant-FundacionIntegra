// Copy de la sesión demo, Inicio y chat (plan de arreglos, decisión 1: sin claves i18n nuevas para no
// recalcular el bundle C4). Texto plano en español, sin HTML. Rol 4 lo revisa y se migra a es.json
// cuando se recalcule el bundle. Nunca promete resultados: el motor decide, el texto solo orienta.
export const DEMO_COPY = {
  gateTitle: 'Bienvenida',
  gateIntro: 'Entre a la demo como la educadora del jardín. Verá a sus familias, sus avances y el chat de situaciones.',
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
  chatAssistant: 'Brújula',
  chatGardenNoData: 'Aún no tengo los datos de su jardín. Intente de nuevo en un momento.',
  chatHistoryLabel: 'Conversación',
  quickTitle: 'Preguntas rápidas',
  quickNoData: 'Por ahora no hay apoyos pendientes para esta familia.',
} as const;

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
