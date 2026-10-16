// Mapeos de PRESENTACIÓN pura (design.md §4.1, §10.4, SUP-036). No cambian posición, orden ni
// filtran listas de C3: solo traducen un enum a ícono, tono y clave i18n (FE-003).
import type {
  AccessState,
  ActionType,
  BenefitResultValue,
  Channel,
  ConversationStatus,
  HousingType,
  InconsistencyCode,
  IncomeBand,
  KpiLevel,
  Level,
  MissingCode,
  NextStep,
  OpportunityOrder,
  PreferredFormat,
  Role,
  TraceResult,
  TrafficLight,
  Zone,
} from '../api/types';
import { ADD_INFO_COPY } from '../api/proposals/addInfoCopy';
import type { CopyKey } from '../i18n/catalog';
import { t, type PlainCopyKey } from '../i18n/copy';

export type Group = 'go' | 'ask' | 'has' | 'other';
export type Tone = Group | 'neutral';
export type IconName = 'check' | 'question' | 'mailbox' | 'clock' | 'info' | 'dash' | 'alert' | 'calendar';

export interface Presentation {
  readonly icon: IconName;
  readonly tone: Tone;
  readonly labelKey: PlainCopyKey;
}

export const GROUP_PRESENTATION: Readonly<Record<Group, Presentation>> = {
  go: { icon: 'check', tone: 'go', labelKey: 'group.go.label' },
  ask: { icon: 'question', tone: 'ask', labelKey: 'group.ask.label' },
  has: { icon: 'mailbox', tone: 'has', labelKey: 'group.has.label' },
  other: { icon: 'info', tone: 'other', labelKey: 'group.other.label' },
};

/** §10.4: estado de acceso → grupo visual. `NO_APLICA` solo aparece en el detalle técnico. */
export const ACCESS_STATE_GROUP: Readonly<Record<AccessState, Group | null>> = {
  ELEGIBLE_SIN_ASIGNACION: 'go',
  PENDIENTE_ANTECEDENTES: 'ask',
  INDETERMINADO: 'ask',
  ASIGNADO: 'has',
  GESTION_EN_CURSO: 'has',
  GESTION_RECHAZADA: 'other',
  SIN_CUPO: 'other',
  NO_APLICA: null,
};

/** Ícono por estado dentro del grupo `has` (buzón = ya lo recibe, reloj = en trámite). */
const ACCESS_STATE_ICON: Readonly<Record<AccessState, IconName>> = {
  ELEGIBLE_SIN_ASIGNACION: 'check',
  PENDIENTE_ANTECEDENTES: 'question',
  INDETERMINADO: 'question',
  ASIGNADO: 'mailbox',
  GESTION_EN_CURSO: 'clock',
  GESTION_RECHAZADA: 'info',
  SIN_CUPO: 'info',
  NO_APLICA: 'dash',
};

export const ACCESS_STATE_KEY: Readonly<Record<AccessState, PlainCopyKey>> = {
  ASIGNADO: 'access_state.asignado',
  GESTION_EN_CURSO: 'access_state.gestion_en_curso',
  GESTION_RECHAZADA: 'access_state.gestion_rechazada',
  ELEGIBLE_SIN_ASIGNACION: 'access_state.elegible_sin_asignacion',
  SIN_CUPO: 'access_state.sin_cupo',
  PENDIENTE_ANTECEDENTES: 'access_state.pendiente_antecedentes',
  INDETERMINADO: 'access_state.indeterminado',
  NO_APLICA: 'access_state.no_aplica',
};

export function accessGroup(state: AccessState): Group | null {
  return ACCESS_STATE_GROUP[state];
}

/** Chip de grupo de una oportunidad (ícono + texto + tono; V-08). */
export function accessPresentation(state: AccessState): Presentation | null {
  const group = ACCESS_STATE_GROUP[state];
  if (group === null) return null;
  return { ...GROUP_PRESENTATION[group], icon: ACCESS_STATE_ICON[state] };
}

export type UrgencyChipKey = Extract<CopyKey, 'chip.urgency.high' | 'chip.urgency.week'>;

/** SUP-036: U ≥ 0,8 → "Urgente"; U ≥ 0,6 → "Esta semana"; si no, ningún chip. Solo presentación. */
export function urgencyChip(urgency: number): UrgencyChipKey | null {
  if (urgency >= 0.8) return 'chip.urgency.high';
  if (urgency >= 0.6) return 'chip.urgency.week';
  return null;
}

export const TRAFFIC_LIGHT_PRESENTATION: Readonly<Record<TrafficLight, Presentation>> = {
  VERDE: { icon: 'check', tone: 'go', labelKey: 'traffic_light.verde' },
  AMARILLO: { icon: 'question', tone: 'ask', labelKey: 'traffic_light.amarillo' },
  AZUL: { icon: 'mailbox', tone: 'has', labelKey: 'traffic_light.azul' },
  SIN_OPORTUNIDADES: { icon: 'dash', tone: 'neutral', labelKey: 'traffic_light.sin_oportunidades' },
};

export const CONVERSATION_STATUS_KEY: Readonly<Record<ConversationStatus, PlainCopyKey>> = {
  PENDIENTE: 'conversation_status.pendiente',
  CONVERSADA: 'conversation_status.conversada',
  EN_COLA: 'conversation_status.en_cola',
};

export const RESULT_KEY: Readonly<Record<BenefitResultValue, PlainCopyKey>> = {
  SI: 'result.si',
  NO: 'result.no',
  INDETERMINADO: 'result.indeterminado',
  NO_APLICA: 'result.no_aplica',
};

export const LEVEL_KEY: Readonly<Record<Level, PlainCopyKey>> = {
  CONFIRMADO: 'level.confirmado',
  PRELIMINAR: 'level.preliminar',
};

export const ACTION_TYPE_KEY: Readonly<Record<ActionType, PlainCopyKey>> = {
  FAMILY_ACTION: 'action_type.family_action',
  AUTOMATIC: 'action_type.automatic',
  FOLLOW_UP: 'action_type.follow_up',
  ASK_FIRST: 'action_type.ask_first',
};

export const ROLE_KEY: Readonly<Record<Role, PlainCopyKey>> = {
  ADULT_REFERENCE: 'role.adult_reference',
  CHILD: 'role.child',
  OTHER_ADULT: 'role.other_adult',
};

export const FORMAT_KEY: Readonly<Record<PreferredFormat, PlainCopyKey>> = {
  TEXT: 'format.text',
  VISUAL: 'format.visual',
  AUDIO: 'format.audio',
};

export const ORDER_KEY: Readonly<Record<OpportunityOrder, PlainCopyKey>> = {
  prioridad: 'order.prioridad',
  urgencia: 'order.urgencia',
  beneficio: 'order.beneficio',
};

export const NEXT_STEP_KEY: Readonly<Record<NextStep, PlainCopyKey>> = {
  GO_TO_INSTITUTION: 'next_step.go_to_institution',
  UPDATE_RSH: 'next_step.update_rsh',
  BRING_DOCUMENTS: 'next_step.bring_documents',
  NONE: 'next_step.none',
};

export const CHANNEL_KEY: Readonly<Record<Channel, PlainCopyKey>> = {
  IN_PERSON: 'channel.in_person',
  GROUP_MEETING: 'channel.group_meeting',
  WHATSAPP_PREVIEW: 'channel.whatsapp_preview',
  PRINTED: 'channel.printed',
};

export const TRACE_RESULT_KEY: Readonly<Record<TraceResult, PlainCopyKey>> = {
  CUMPLE: 'trace_result.cumple',
  NO_CUMPLE: 'trace_result.no_cumple',
  INDETERMINADO: 'trace_result.indeterminado',
};

export const MISSING_CODE_KEY: Readonly<Record<MissingCode, PlainCopyKey>> = {
  composition: 'context.missing.composition',
  child_age: 'context.missing.child_age',
  siblings_under_6: 'context.missing.siblings_under_6',
  siblings_6_14: 'context.missing.siblings_6_14',
  siblings_15_18: 'context.missing.siblings_15_18',
  rsh_status: 'context.missing.rsh_status',
  rsh_band: 'context.missing.rsh_band',
  income_band: 'context.missing.income_band',
  ssyo_participation: 'context.missing.ssyo_participation',
  chile_crece_contigo_access: 'context.missing.chile_crece_contigo_access',
  last_health_control_date: 'context.missing.last_health_control_date',
  possible_disability: 'context.missing.possible_disability',
  therapy: 'context.missing.therapy',
  housing_type: 'context.missing.housing_type',
  pregnancy: 'context.missing.pregnancy',
  adult_over_65: 'context.missing.adult_over_65',
  employment_or_pension: 'context.missing.employment_or_pension',
  water_difficulty: 'context.missing.water_difficulty',
  food_difficulty: 'context.missing.food_difficulty',
};

const ENGINE_MISSING_LABEL: Readonly<Record<string, string>> = ADD_INFO_COPY.missingEngine;

const has = (map: object, key: string): boolean => Object.prototype.hasOwnProperty.call(map, key);

/** Texto simple de un código faltante (C3 o motor); desconocido → null (nunca se muestra el código). */
function missingCodeLabel(code: string): string | null {
  if (has(MISSING_CODE_KEY, code)) return t(MISSING_CODE_KEY[code as MissingCode]);
  if (has(ENGINE_MISSING_LABEL, code)) return ENGINE_MISSING_LABEL[code] ?? null;
  if (code.startsWith('residencia_')) return ADD_INFO_COPY.missingEngine.residencia;
  return null;
}

/** Datos faltantes en lenguaje simple, sin repetir textos; los desconocidos dan UN genérico. */
export function missingCodeLabels(codes: readonly string[]): string[] {
  const labels = codes.map((code) => missingCodeLabel(code) ?? t('family.missing_generic'));
  return [...new Set(labels)];
}

/** Solo los datos faltantes con texto propio, sin repetir; los desconocidos se omiten (sin genérico). */
export function knownMissingLabels(codes: readonly string[]): string[] {
  const labels = codes.map(missingCodeLabel).filter((label): label is string => label !== null);
  return [...new Set(labels)];
}

export const INCONSISTENCY_KEY: Readonly<Record<InconsistencyCode, PlainCopyKey>> = {
  SIBLINGS_UNDER_6_MISMATCH: 'context.inconsistency.siblings_under_6_mismatch',
  SIBLINGS_6_14_MISMATCH: 'context.inconsistency.siblings_6_14_mismatch',
  SIBLINGS_15_18_MISMATCH: 'context.inconsistency.siblings_15_18_mismatch',
  RSH_STATUS_MISMATCH: 'context.inconsistency.rsh_status_mismatch',
  HOUSEHOLD_SIZE_MISMATCH: 'context.inconsistency.household_size_mismatch',
};

export const INCOME_BAND_KEY: Readonly<Record<IncomeBand, PlainCopyKey>> = {
  UNDER_110K: 'income_band.under_110k',
  '110K_250K': 'income_band.110k_250k',
  '250K_400K': 'income_band.250k_400k',
  OVER_400K: 'income_band.over_400k',
};

export const HOUSING_KEY: Readonly<Record<HousingType, PlainCopyKey>> = {
  ADEQUATE: 'housing.adequate',
  CAMP_OR_OCCUPATION: 'housing.camp_or_occupation',
  ROOM_IN_OTHER_HOME: 'housing.room_in_other_home',
  OTHER: 'housing.other',
  UNKNOWN: 'housing.unknown',
};

export const ZONE_KEY: Readonly<Record<Zone, PlainCopyKey>> = {
  URBANA: 'home.zone.urbana',
  RURAL: 'home.zone.rural',
};

export const KPI_LEVEL_KEY: Readonly<Record<KpiLevel, PlainCopyKey>> = {
  jardin: 'kpi.level.jardin',
  comuna: 'kpi.level.comuna',
  region: 'kpi.level.region',
  nacional: 'kpi.level.nacional',
};
