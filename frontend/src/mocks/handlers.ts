// Mock-SERVIDOR C3 (design.md §8) con MSW 3. Los mismos handlers sirven al transporte en proceso
// del navegador (getResponse) y a Vitest (setupServer). Este es el ÚNICO lugar del frontend donde
// se recalculan conteos y porcentajes, en su rol de servidor simulado (FE-003; el lint prohíbe
// importar src/mocks/** desde features/, data/ y domain/).
import { http, HttpResponse, type HttpHandler } from 'msw';
import { formats } from '../api/contract/runtime.js';
import {
  validateAssistantPublicRequest,
  validateConversationRequest,
  validateFamilyGenerationPublicRequest,
  validatePreevaluationRequest,
  validateTextractFlyerRequestV1,
} from '../api/generated/validators.gen.js';
import type {
  AssistantEnvelope,
  ConversationEnvelope,
  ConversationRecord,
  FamiliaContextEnvelope,
  FamiliaDetailEnvelope,
  FamiliaListEnvelope,
  FamilyDetail,
  FamilySummary,
  FlyerDraftEnvelope,
  JardinListEnvelope,
  JardinSummary,
  KpiEnvelope,
  KpiLevel,
  MessageGenerationEnvelope,
  OpportunityListEnvelope,
  PreevaluationEnvelope,
  ScriptGenerationEnvelope,
  TrafficLight,
} from '../api/types';
import { MISSING_CODE_FIELD } from '../api/proposals/addInfo';
import { validateAddFamilyInfoRequestV1 } from '../api/proposals/generated/validators.gen.js';
import type { AddFamilyInfoRequestV1 } from '../api/proposals/types';
import { isValidId } from '../domain/ids';
import { hasFixture, payloadOf } from './fixtureStore';
import addInfoFixture from './proposals/addFamiliaAntecedentes.FAM-SIM-E3-00002.json';
import type { ScenarioId } from './scenarios';
import { messageWithHttpCitation } from './variants';

const API = '*/api/v1';
export const BASE_SNAPSHOT = 'SNAP-SIM-DEMO-001';
export const NEXT_SNAPSHOT = 'SNAP-SIM-DEMO-002';
const ORDERS = ['prioridad', 'urgencia', 'beneficio'] as const;
const KPI_LEVELS: readonly KpiLevel[] = ['jardin', 'comuna', 'region', 'nacional'];

/** Ficha base (fixture escrito a mano) que el servidor clona para cada semáforo. */
const BASE_FAMILY: Readonly<Record<TrafficLight, string>> = {
  VERDE: 'FAM-SIM-E3-00001',
  AMARILLO: 'FAM-SIM-E3-00002',
  AZUL: 'FAM-SIM-E3-00003',
  SIN_OPORTUNIDADES: 'FAM-SIM-E3-00004',
};
const NEW_FAMILY_BASE = 'FAM-SIM-E3-00002';
const FAMILY_PAGES: Readonly<Record<string, readonly string[]>> = {
  'JAR-SIM-E3-00001': ['listFamiliasByJardin.JAR-SIM-E3-00001.p1', 'listFamiliasByJardin.JAR-SIM-E3-00001.p2'],
  'JAR-SIM-E3-00003': ['listFamiliasByJardin.JAR-SIM-E3-00003'],
};
/** Conversaciones sembradas por el servidor (origin SIMULADO_DEMO, SUP-033). */
const SEEDS = ['createConversacion.seed.FAM-SIM-E3-00005', 'createConversacion.seed.FAM-SIM-E3-00007'];
const KNOWN_ASSETS = new Set(['ASSET-SIM-001']);

interface FamilyRecord {
  readonly familyId: string;
  readonly gardenId: string;
  /** Fixture de ficha/contexto/oportunidades que se clona. */
  readonly base: string;
  readonly isNew: boolean;
}

interface FamilyPages {
  /** Fixture de cada página; los ítems se releen y se les aplica el estado del servidor. */
  readonly names: readonly string[];
  readonly cursors: (string | null)[];
}

interface StoredResponse {
  readonly scope: string;
  readonly canonical: string;
  readonly status: number;
  readonly body: unknown;
}

interface ServerState {
  gardens: JardinSummary[];
  pages: Map<string, FamilyPages>;
  families: Map<string, FamilyRecord>;
  /** Fichas re-evaluadas por la operación propuesta `addFamiliaAntecedentes` (DEC-039). */
  details: Map<string, FamilyDetail>;
  informed: Set<string>;
  conversations: ConversationRecord[];
  newFamiliesInformed: Set<string>;
  idempotency: Map<string, StoredResponse>;
  conversationCounter: number;
  newFamilyCounter: number;
  /** Respuestas 2xx emitidas (escenario snapshotChange). */
  responses: number;
  preevalLost: boolean;
}

function createState(): ServerState {
  const gardens = payloadOf<JardinListEnvelope>('listJardines').items;
  const pages = new Map<string, FamilyPages>();
  const families = new Map<string, FamilyRecord>();
  const informed = new Set<string>();
  for (const [gardenId, names] of Object.entries(FAMILY_PAGES)) {
    const envelopes = names.map((name) => payloadOf<FamiliaListEnvelope>(name));
    pages.set(gardenId, { names, cursors: envelopes.map((e) => e.next_cursor) });
    for (const item of envelopes.flatMap((e) => e.items)) {
      families.set(item.family_id, { familyId: item.family_id, gardenId, base: BASE_FAMILY[item.traffic_light], isNew: false });
      if (item.conversation_status === 'CONVERSADA') informed.add(item.family_id);
    }
  }
  const conversations = SEEDS.map((name) => payloadOf<ConversationEnvelope>(name).data);
  for (const seed of conversations) informed.add(seed.family_id);
  return {
    gardens,
    pages,
    families,
    details: new Map(),
    informed,
    conversations,
    newFamiliesInformed: new Set(),
    idempotency: new Map(),
    conversationCounter: 0,
    newFamilyCounter: 0,
    responses: 0,
    preevalLost: false,
  };
}

/** JSON canónico (claves ordenadas) para comparar cuerpos en la idempotencia. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    const entries = Object.keys(value as Record<string, unknown>)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(value);
}

/** Códigos faltantes que el cuerpo declara con un valor (null/UNKNOWN = "No sé": no resuelve). */
function declaredCodes(body: AddFamilyInfoRequestV1): Set<string> {
  const declared = new Set<string>();
  for (const [code, field] of Object.entries(MISSING_CODE_FIELD)) {
    if (field === undefined) continue;
    const value = body[field];
    if (value !== undefined && value !== null && value !== 'UNKNOWN') declared.add(code);
  }
  return declared;
}

interface Resolvable {
  readonly result: string;
  readonly level: string | null;
  readonly access_state: string;
  readonly missing_codes: readonly string[];
}

/**
 * SIMULACIÓN SINTÉTICA del mock-servidor (rol de servidor; el motor real es de Rol 1/2): un beneficio
 * cuyos faltantes quedan TODOS declarados pasa a SI PRELIMINAR (ELEGIBLE_SIN_ASIGNACION si estaba
 * INDETERMINADO o PENDIENTE_ANTECEDENTES); si quedan faltantes, solo se quitan los declarados.
 */
function resolveDeclared<T extends Resolvable>(row: T, declared: ReadonlySet<string>): T {
  const remaining = row.missing_codes.filter((code) => !declared.has(code));
  if (remaining.length === row.missing_codes.length) return row;
  if (remaining.length > 0) return { ...row, missing_codes: remaining } as T;
  if (row.result === 'INDETERMINADO' || row.access_state === 'PENDIENTE_ANTECEDENTES') {
    return { ...row, result: 'SI', level: 'PRELIMINAR', access_state: 'ELEGIBLE_SIN_ASIGNACION', missing_codes: [] } as T;
  }
  return { ...row, level: row.result === 'SI' ? 'PRELIMINAR' : row.level, missing_codes: [] } as T;
}

export function reevaluateWithDeclared(detail: FamilyDetail, body: AddFamilyInfoRequestV1): FamilyDetail {
  const declared = declaredCodes(body);
  return {
    ...detail,
    benefit_results: detail.benefit_results.map((result) => {
      const next = resolveDeclared(result, declared);
      if (next === result || next.missing_codes.length > 0) return next;
      return { ...next, trace: next.trace.map((item) => (item.result === 'INDETERMINADO' ? { ...item, result: 'CUMPLE' as const } : item)) };
    }),
    top_opportunities: detail.top_opportunities.map((opportunity) => resolveDeclared(opportunity, declared)),
  };
}

/** Porcentaje con 1 decimal; null si el total es 0 (rol de servidor). */
function percentage(part: number, total: number): number | null {
  return total === 0 ? null : Math.round((part * 1000) / total) / 10;
}

export interface MockServer {
  readonly handlers: HttpHandler[];
  /** Restaura el estado de servidor y la tabla de idempotencia. */
  reset(): void;
  setScenario(scenario: ScenarioId): void;
  scenario(): ScenarioId;
  /** Solo lectura para pruebas del mock-servidor. */
  snapshotOfState(): { informed: string[]; conversations: number; newFamilies: number };
}

export function createMockServer(options: { scenario?: ScenarioId } = {}): MockServer {
  let scenario: ScenarioId = options.scenario ?? 'default';
  let state = createState();

  const currentSnapshot = () => (scenario === 'snapshotChange' && state.responses > 0 ? NEXT_SNAPSHOT : BASE_SNAPSHOT);

  const ok = <T extends object>(body: T, status = 200, snapshot?: string): Response => {
    const meta = (body as { meta?: { snapshot_id: string } }).meta;
    if (meta !== undefined) meta.snapshot_id = snapshot ?? currentSnapshot();
    state.responses += 1;
    return HttpResponse.json(body, { status });
  };

  const fail = (status: 401 | 403 | 404 | 409 | 422 | 429 | 503): Response =>
    HttpResponse.json(payloadOf(`error.${status}`), { status });

  const readJson = async (request: Request): Promise<{ ok: true; value: unknown } | { ok: false }> => {
    try {
      return { ok: true, value: JSON.parse(await request.text()) as unknown };
    } catch {
      return { ok: false };
    }
  };

  const gardenOf = (gardenId: string) => state.gardens.find((g) => g.garden_id === gardenId);

  /** Ficha del servidor: la re-evaluada si existe; si no, el fixture base con IDs y estado actuales. */
  const detailEnvelope = (record: FamilyRecord): FamiliaDetailEnvelope => {
    const body = payloadOf<FamiliaDetailEnvelope>(`getFamilia.${record.base}`);
    const stored = state.details.get(record.familyId);
    if (stored !== undefined) body.data = structuredClone(stored);
    body.data.family_id = record.familyId;
    body.data.garden_id = record.gardenId;
    body.data.informed = state.informed.has(record.familyId);
    return body;
  };

  const summaryWithState = (item: FamilySummary): FamilySummary =>
    state.informed.has(item.family_id) ? { ...item, conversation_status: 'CONVERSADA' } : item;

  const opportunityIdsOf = (record: FamilyRecord): Set<string> =>
    new Set(payloadOf<OpportunityListEnvelope>(`listOportunidades.${record.base}.prioridad`).items.map((o) => o.benefit_id));

  /**
   * Idempotencia por operación (y familia en conversaciones): misma clave y cuerpo → misma
   * respuesta sin efectos nuevos; misma clave con otro cuerpo → 409.
   */
  const replay = (key: string, scope: string, canonical: string): Response | 'conflict' | null => {
    const stored = state.idempotency.get(`${scope}|${key}`);
    if (stored === undefined) return null;
    if (stored.canonical !== canonical) return 'conflict';
    return HttpResponse.json(structuredClone(stored.body) as Record<string, unknown>, { status: stored.status });
  };

  const handlers: HttpHandler[] = [
    http.get(`${API}/jardines`, ({ request }) => {
      const query = new URL(request.url).searchParams;
      const limit = query.get('limit');
      if (limit !== null && !(/^\d{1,3}$/.test(limit) && Number(limit) >= 1 && Number(limit) <= 100)) return fail(422);
      // Todos los jardines Demo caben en una página: cualquier cursor es desconocido.
      if (query.get('cursor') !== null) return fail(422);
      const body = payloadOf<JardinListEnvelope>('listJardines');
      body.items = structuredClone(state.gardens);
      return ok(body);
    }),

    http.get(`${API}/jardines/:id/familias`, ({ request, params }) => {
      const gardenId = String(params.id);
      if (!isValidId(gardenId)) return fail(422);
      if (gardenOf(gardenId) === undefined) return fail(404);
      if (scenario === 'error503') return fail(503);
      const query = new URL(request.url).searchParams;
      const cursor = query.get('cursor');
      const pages = state.pages.get(gardenId);
      const body = payloadOf<FamiliaListEnvelope>('listFamiliasByJardin.JAR-SIM-E3-00001.p1');
      if (pages === undefined || scenario === 'empty') {
        if (cursor !== null) return fail(422);
        body.items = [];
        body.next_cursor = null;
        return ok(body);
      }
      const index = cursor === null ? 0 : pages.cursors.indexOf(cursor) + 1;
      const name = pages.names[index];
      if (name === undefined || (cursor !== null && index === 0)) return fail(422);
      const page = payloadOf<FamiliaListEnvelope>(name);
      page.items = page.items.map(summaryWithState);
      const pageSnapshot = scenario === 'snapshotPageChange' && index > 0 ? NEXT_SNAPSHOT : undefined;
      return ok(page, 200, pageSnapshot);
    }),

    http.get(`${API}/familias/:id`, ({ params }) => {
      const familyId = String(params.id);
      const record = state.families.get(familyId);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      if (scenario === 'html403') {
        return new HttpResponse('<!doctype html><title>403</title><h1>Request blocked</h1>', {
          status: 403,
          headers: { 'Content-Type': 'text/html; charset=utf-8' },
        });
      }
      return ok(detailEnvelope(record));
    }),

    // Operación PROPUESTA (DEC-039, fuera de C3): datos declarados → ficha re-evaluada (PRELIMINAR).
    http.post(`${API}/familias/:id/antecedentes`, async ({ request, params }) => {
      const familyId = String(params.id);
      const key = request.headers.get('Idempotency-Key');
      if (key === null || !formats.uuid(key)) return fail(422);
      const parsed = await readJson(request);
      if (!parsed.ok || !validateAddFamilyInfoRequestV1(parsed.value)) return fail(422);
      const record = state.families.get(familyId);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      if (scenario === 'addInfo503') return fail(503);
      const canonical = canonicalJson(parsed.value);
      const scope = `addinfo:${familyId}`;
      const replayed = replay(key, scope, canonical);
      if (replayed === 'conflict') return fail(409);
      if (replayed !== null) return replayed;

      const current = detailEnvelope(record);
      const updated = reevaluateWithDeclared(current.data, parsed.value);
      state.details.set(familyId, structuredClone(updated));
      const response = structuredClone(addInfoFixture.payload) as unknown as FamiliaDetailEnvelope;
      response.meta.snapshot_id = currentSnapshot();
      response.data = updated;
      state.idempotency.set(`${scope}|${key}`, { scope, canonical, status: 200, body: structuredClone(response) });
      return ok(response);
    }),

    http.get(`${API}/familias/:id/contexto`, ({ params }) => {
      const familyId = String(params.id);
      const record = state.families.get(familyId);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      const body = payloadOf<FamiliaContextEnvelope>(`getContextoFamilia.${record.base}`);
      body.data.family_id = familyId;
      return ok(body);
    }),

    http.get(`${API}/familias/:id/oportunidades`, ({ request, params }) => {
      const familyId = String(params.id);
      const record = state.families.get(familyId);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      const orden = new URL(request.url).searchParams.get('orden') ?? 'prioridad';
      if (!(ORDERS as readonly string[]).includes(orden)) return fail(422);
      const name = hasFixture(`listOportunidades.${record.base}.${orden}`)
        ? `listOportunidades.${record.base}.${orden}`
        : `listOportunidades.${record.base}.prioridad`;
      return ok(payloadOf<OpportunityListEnvelope>(name));
    }),

    http.post(`${API}/familias/nueva/preevaluacion`, async ({ request }) => {
      const key = request.headers.get('Idempotency-Key');
      if (key === null || !formats.uuid(key)) return fail(422);
      const parsed = await readJson(request);
      if (!parsed.ok || !validatePreevaluationRequest(parsed.value)) return fail(422);
      const body = parsed.value;
      const garden = gardenOf(body.garden_id);
      if (garden === undefined || garden.commune_id !== body.commune_id) return fail(422);
      const canonical = canonicalJson(body);
      const replayed = replay(key, 'preeval', canonical);
      if (replayed === 'conflict') return fail(409);
      if (replayed !== null) return replayed;

      state.newFamilyCounter += 1;
      const familyId = `FAM-SIM-E3-${String(100 + state.newFamilyCounter).padStart(5, '0')}`;
      state.families.set(familyId, { familyId, gardenId: garden.garden_id, base: NEW_FAMILY_BASE, isNew: true });
      const response = payloadOf<PreevaluationEnvelope>('createPreevaluacion');
      response.meta.snapshot_id = currentSnapshot();
      response.data.family_id = familyId;
      state.idempotency.set(`preeval|${key}`, { scope: 'preeval', canonical, status: 200, body: structuredClone(response) });
      if (scenario === 'preevalTimeout' && !state.preevalLost) {
        // El servidor registró el envío, pero la respuesta "se pierde": fetch recibe un error de red.
        state.preevalLost = true;
        return HttpResponse.error();
      }
      return ok(response);
    }),

    http.post(`${API}/familias/:id/guion`, async ({ request, params }) => {
      const familyId = String(params.id);
      const record = state.families.get(familyId);
      const parsed = await readJson(request);
      if (!parsed.ok || !validateFamilyGenerationPublicRequest(parsed.value)) return fail(422);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      const allowed = opportunityIdsOf(record);
      if (!parsed.value.benefit_ids.every((id) => allowed.has(id))) return fail(422);
      const body = payloadOf<ScriptGenerationEnvelope>(
        scenario === 'providerTemplate' ? 'createGuion.plantilla' : 'createGuion.bedrock',
      );
      body.content.benefit_ids = [...parsed.value.benefit_ids];
      return ok(body);
    }),

    http.post(`${API}/familias/:id/mensaje`, async ({ request, params }) => {
      const familyId = String(params.id);
      const record = state.families.get(familyId);
      const parsed = await readJson(request);
      if (!parsed.ok || !validateFamilyGenerationPublicRequest(parsed.value)) return fail(422);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      const allowed = opportunityIdsOf(record);
      if (!parsed.value.benefit_ids.every((id) => allowed.has(id))) return fail(422);
      let body: MessageGenerationEnvelope;
      if (scenario === 'invalidCitation') body = messageWithHttpCitation() as MessageGenerationEnvelope;
      else if (scenario === 'adversarialCard') body = payloadOf('createMensaje.adversarial');
      else if (scenario === 'providerTemplate') body = payloadOf('createMensaje.plantilla');
      else body = payloadOf('createMensaje.bedrock');
      body.content.benefit_ids = [...parsed.value.benefit_ids];
      return ok(body);
    }),

    http.post(`${API}/familias/:id/conversaciones`, async ({ request, params }) => {
      const familyId = String(params.id);
      const key = request.headers.get('Idempotency-Key');
      if (key === null || !formats.uuid(key)) return fail(422);
      const parsed = await readJson(request);
      if (!parsed.ok || !validateConversationRequest(parsed.value)) return fail(422);
      const record = state.families.get(familyId);
      if (!isValidId(familyId) || record === undefined) return fail(404);
      if (scenario === 'conv409') return fail(409);
      if (scenario === 'conv401') return fail(401);
      if (scenario === 'conv503') return fail(503);
      if (scenario === 'gateway429') return HttpResponse.json({ message: 'Too Many Requests' }, { status: 429 });
      const body = parsed.value;
      const allowed = opportunityIdsOf(record);
      if (!body.benefit_ids.every((id) => allowed.has(id))) return fail(422);
      if (body.snapshot_id !== currentSnapshot()) return fail(409);
      const canonical = canonicalJson(body);
      const scope = `conv:${familyId}`;
      const replayed = replay(key, scope, canonical);
      if (replayed === 'conflict') return fail(409);
      if (replayed !== null) return replayed;

      state.conversationCounter += 1;
      const conversation: ConversationRecord = {
        conversation_id: `00000000-0000-4000-8000-${String(state.conversationCounter).padStart(12, '0')}`,
        family_id: familyId,
        garden_id: record.gardenId,
        benefit_ids: [...body.benefit_ids],
        next_step: body.next_step,
        channel: body.channel,
        occurred_at: body.occurred_at,
        snapshot_id: body.snapshot_id,
        origin: body.origin,
        status: 'CONFIRMED',
      };
      state.conversations.push(conversation);
      // Primer 201 de una familia PENDIENTE: el servidor actualiza su estado de forma coherente.
      if (!state.informed.has(familyId)) {
        state.informed.add(familyId);
        if (record.isNew) {
          state.newFamiliesInformed.add(familyId);
        } else {
          const garden = gardenOf(record.gardenId);
          if (garden !== undefined) {
            garden.families_informed += 1;
            garden.informed_percentage = percentage(garden.families_informed, garden.families_total);
          }
        }
      }
      const response = payloadOf<ConversationEnvelope>('createConversacion');
      response.meta.snapshot_id = currentSnapshot();
      response.data = conversation;
      state.idempotency.set(`${scope}|${key}`, { scope, canonical, status: 201, body: structuredClone(response) });
      return ok(response, 201);
    }),

    http.get(`${API}/kpi`, ({ request }) => {
      const query = new URL(request.url).searchParams;
      const nivel = query.get('nivel') as KpiLevel | null;
      if (nivel === null || !KPI_LEVELS.includes(nivel)) return fail(422);
      const id = query.get('id');
      if (nivel === 'nacional' ? id !== null : id === null || !isValidId(id)) return fail(422);
      const desde = query.get('desde');
      const hasta = query.get('hasta');
      if ((desde !== null && !formats.date(desde)) || (hasta !== null && !formats.date(hasta))) return fail(422);
      if (desde !== null && hasta !== null && desde > hasta) return fail(422);
      const inScope = state.gardens.filter((g) =>
        nivel === 'jardin' ? g.garden_id === id : nivel === 'comuna' ? g.commune_id === id : nivel === 'region' ? g.region_id === id : true,
      );
      if (inScope.length === 0) return fail(403);
      const fixtureName =
        scenario === 'kpiSuppressed' ? 'getKpi.suppressed' : scenario === 'kpiNull' ? 'getKpi.nulls' : 'getKpi';
      const body = payloadOf<KpiEnvelope>(fixtureName);
      body.data.level = nivel;
      body.data.scope_id = nivel === 'nacional' ? null : id;
      if (desde !== null) body.data.period_start = desde;
      if (hasta !== null) body.data.period_end = hasta;
      if (fixtureName === 'getKpi') {
        // Rol de servidor: agrega conteos de los jardines del alcance (mismo estado que Inicio).
        const scopeGardens = new Set(inScope.map((g) => g.garden_id));
        const total = inScope.reduce((sum, g) => sum + g.families_total, 0);
        const informedCount = inScope.reduce((sum, g) => sum + g.families_informed, 0);
        const newFamilies = [...state.families.values()].filter((f) => f.isNew && scopeGardens.has(f.gardenId));
        const newInformed = newFamilies.filter((f) => state.newFamiliesInformed.has(f.familyId)).length;
        body.data.total_families = total;
        body.data.informed_families = informedCount;
        body.data.informed_percentage = percentage(informedCount, total);
        body.data.total_new_families = newFamilies.length;
        body.data.informed_new_families = newInformed;
        body.data.informed_new_percentage = percentage(newInformed, newFamilies.length);
      }
      return ok(body);
    }),

    http.post(`${API}/asistente`, async ({ request }) => {
      const parsed = await readJson(request);
      if (!parsed.ok || !validateAssistantPublicRequest(parsed.value)) return fail(422);
      if (scenario === 'assistantDeterministic') return ok(payloadOf<AssistantEnvelope>('askCatalogAssistant.deterministic'));
      const body = payloadOf<AssistantEnvelope>('askCatalogAssistant.catalog-info');
      if (scenario === 'providerTemplate') {
        body.provider = 'PLANTILLA';
        body.warnings = ['LLM_UNAVAILABLE'];
      }
      return ok(body);
    }),

    http.post(`${API}/catalogo/ingesta-afiche`, async ({ request }) => {
      const parsed = await readJson(request);
      if (!parsed.ok || !validateTextractFlyerRequestV1(parsed.value)) return fail(422);
      if (!KNOWN_ASSETS.has(parsed.value.synthetic_asset_id)) return fail(409);
      const body = payloadOf<FlyerDraftEnvelope>('ingestSyntheticFlyer');
      body.data.synthetic_asset_id = parsed.value.synthetic_asset_id;
      return ok(body);
    }),
  ];

  return {
    handlers,
    reset() {
      state = createState();
    },
    setScenario(next) {
      scenario = next;
    },
    scenario: () => scenario,
    snapshotOfState: () => ({
      informed: [...state.informed].sort(),
      conversations: state.conversations.length,
      newFamilies: [...state.families.values()].filter((f) => f.isNew).length,
    }),
  };
}
