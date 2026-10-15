// Datos de prueba: SOLO derivan de src/mocks/fixtures/*.json (design.md §8). Se clonan o se
// modifican campos puntuales; no se definen hogares nuevos.
import type {
  ConversationRequest,
  FamiliaDetailEnvelope,
  FamiliaListEnvelope,
  JardinListEnvelope,
  MessageGenerationEnvelope,
  PreevaluationRequest,
} from '../api/types';
import { FIXTURES, payloadOf } from '../mocks/fixtureStore';
import * as variants from '../mocks/variants';

export const data_classification = 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON';

export { FIXTURES, payloadOf, variants };

export const jardines = (): JardinListEnvelope => payloadOf('listJardines');
export const familiasPage1 = (): FamiliaListEnvelope => payloadOf('listFamiliasByJardin.JAR-SIM-E3-00001.p1');
export const familiasPage2 = (): FamiliaListEnvelope => payloadOf('listFamiliasByJardin.JAR-SIM-E3-00001.p2');
export const fichaBrecha = (): FamiliaDetailEnvelope => payloadOf('getFamilia.FAM-SIM-E3-00001');
export const fichaPreguntar = (): FamiliaDetailEnvelope => payloadOf('getFamilia.FAM-SIM-E3-00002');
export const fichaYaLoTiene = (): FamiliaDetailEnvelope => payloadOf('getFamilia.FAM-SIM-E3-00003');
export const fichaSinOportunidades = (): FamiliaDetailEnvelope => payloadOf('getFamilia.FAM-SIM-E3-00004');
export const mensajeBedrock = (): MessageGenerationEnvelope => payloadOf('createMensaje.bedrock');
export const mensajeAdversarial = (): MessageGenerationEnvelope => payloadOf('createMensaje.adversarial');

/** Jardín "raro": porcentaje que no calza con los conteos (la UI debe mostrarlo tal cual). */
export function jardinesConPorcentajeRaro(): JardinListEnvelope {
  const body = jardines();
  const first = body.items[0];
  if (first !== undefined) first.informed_percentage = 97.5;
  return body;
}

/** Cuerpo de conversación válido derivado de la ficha brecha (top tres, IN_PERSON). */
export function conversationRequest(overrides: Partial<ConversationRequest> = {}): ConversationRequest {
  const ficha = fichaBrecha();
  return {
    benefit_ids: ficha.data.top_opportunities.map((o) => o.benefit_id),
    next_step: 'GO_TO_INSTITUTION',
    channel: 'IN_PERSON',
    occurred_at: '2026-10-14T10:00:00-03:00',
    snapshot_id: ficha.meta.snapshot_id,
    origin: 'REAL_DEMO',
    ...overrides,
  };
}

/** Preevaluación con todas las claves; "No sé" → null (SUP-034), datos inventados. */
export function preevaluationRequest(overrides: Partial<PreevaluationRequest> = {}): PreevaluationRequest {
  const garden = jardines().items[0];
  return {
    data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON',
    garden_id: garden?.garden_id ?? 'JAR-SIM-E3-00001',
    commune_id: garden?.commune_id ?? 'COM-001',
    demo_notice_accepted: true,
    child_age: 4,
    siblings_under_6: 0,
    siblings_6_14: 1,
    siblings_15_18: null,
    has_rsh: true,
    rsh_band: 40,
    household_income_band: 'UNDER_110K',
    ssyo_participation: null,
    chile_crece_contigo_access: true,
    last_child_health_control_date: '2026-09-01',
    child_possible_disability: null,
    child_in_therapy: false,
    housing_type: 'UNKNOWN',
    household_pregnancy: false,
    household_has_adult_over_65: false,
    household_formal_employment_or_pension: true,
    household_water_payment_difficulty: null,
    household_food_purchase_difficulty: false,
    ...overrides,
  };
}
