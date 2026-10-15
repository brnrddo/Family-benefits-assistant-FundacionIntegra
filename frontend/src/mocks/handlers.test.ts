// Mock-servidor (§8): validación de requests, idempotencia, recálculos y escenarios.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as client from '../api/client';
import { createFetchTransport, setTransport } from '../api/transport';
import { createNoneAdapter } from '../auth/none';
import { createSession } from '../auth/session';
import { log } from '../lib/log';
import { conversationRequest, preevaluationRequest } from '../test/fixtures';
import { mockServer, server, TEST_API_BASE } from '../test/mswServer';
import { TEST_IDEMPOTENCY_KEY } from '../test/operations';
import { canonicalJson, createMockServer, NEXT_SNAPSHOT } from './handlers';
import { parseScenario, readScenarioOnce, resetScenarioForTests, scenarioLatency } from './scenarios';
import { createMockTransport, startBrowserMocks } from './transport';

const OTHER_KEY = '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d';

beforeEach(() => {
  setTransport(createFetchTransport({ baseUrl: TEST_API_BASE, session: createSession(createNoneAdapter()) }));
});

describe('mock-servidor — idempotencia y estado', () => {
  it('primer 201 de una familia PENDIENTE sube conteos, porcentaje y KPI del servidor', async () => {
    const before = await client.listJardines();
    expect(before.body.items[0]).toMatchObject({ families_informed: 2, informed_percentage: 25 });
    await client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    const after = await client.listJardines();
    expect(after.body.items[0]).toMatchObject({ families_total: 8, families_informed: 3, informed_percentage: 37.5 });
    const familias = await client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001' });
    expect(familias.body.items.find((f) => f.family_id === 'FAM-SIM-E3-00001')?.conversation_status).toBe('CONVERSADA');
    const ficha = await client.getFamilia({ familyId: 'FAM-SIM-E3-00001' });
    expect(ficha.body.data.informed).toBe(true);
    for (const [nivel, id] of [['jardin', 'JAR-SIM-E3-00001'], ['comuna', 'COM-001'], ['region', 'REG-SIM-01']] as const) {
      const kpi = await client.getKpi({ nivel, id });
      expect(kpi.body.data).toMatchObject({ total_families: 8, informed_families: 3, informed_percentage: 37.5, scope_id: id, level: nivel });
    }
    const nacional = await client.getKpi({ nivel: 'nacional' });
    expect(nacional.body.data).toMatchObject({ total_families: 9, informed_families: 3, informed_percentage: 33.3, scope_id: null });
  });

  it('misma clave y cuerpo → misma respuesta sin efectos nuevos; otro cuerpo → 409', async () => {
    const first = await client.createConversacion({ familyId: 'FAM-SIM-E3-00002', body: conversationRequest({ benefit_ids: ['BEN-003'] }), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    const again = await client.createConversacion({ familyId: 'FAM-SIM-E3-00002', body: conversationRequest({ benefit_ids: ['BEN-003'] }), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    expect(again.status).toBe(201);
    expect(again.body).toEqual(first.body);
    expect(mockServer.snapshotOfState().conversations).toBe(3); // 2 sembradas + 1
    await expect(
      client.createConversacion({ familyId: 'FAM-SIM-E3-00002', body: conversationRequest({ benefit_ids: ['BEN-005'] }), idempotencyKey: TEST_IDEMPOTENCY_KEY }),
    ).rejects.toMatchObject({ kind: 'http', status: 409 });
    const jardines = await client.listJardines();
    expect(jardines.body.items[0]?.families_informed).toBe(3);
  });

  it('una segunda conversación de una familia ya conversada no vuelve a sumar', async () => {
    await client.createConversacion({ familyId: 'FAM-SIM-E3-00005', body: conversationRequest(), idempotencyKey: OTHER_KEY });
    const jardines = await client.listJardines();
    expect(jardines.body.items[0]?.families_informed).toBe(2);
  });

  it('valida el request: beneficio ajeno → 422; snapshot viejo → 409; familia inexistente → 404', async () => {
    await expect(client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest({ benefit_ids: ['BEN-999'] }), idempotencyKey: OTHER_KEY })).rejects.toMatchObject({ status: 422 });
    await expect(client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest({ snapshot_id: 'SNAP-SIM-DEMO-000' }), idempotencyKey: OTHER_KEY })).rejects.toMatchObject({ status: 409 });
    await expect(client.getFamilia({ familyId: 'FAM-SIM-E3-09999' })).rejects.toMatchObject({ status: 404, requestId: 'REQ-SIM-ERR-404' });
    await expect(client.getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-09999' })).rejects.toMatchObject({ status: 403 });
    await expect(client.listJardines({ cursor: 'CURSOR-DESCONOCIDO' })).rejects.toMatchObject({ status: 422 });
  });

  it('preevaluación: crea familia sintética, suma total_new_families y luego informed_new al conversar', async () => {
    const result = await client.createPreevaluacion({ body: preevaluationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    expect(result.body.data.family_id).toBe('FAM-SIM-E3-00101');
    const replay = await client.createPreevaluacion({ body: preevaluationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    expect(replay.body.data.family_id).toBe('FAM-SIM-E3-00101');
    await expect(client.createPreevaluacion({ body: preevaluationRequest({ child_age: 5 }), idempotencyKey: TEST_IDEMPOTENCY_KEY })).rejects.toMatchObject({ status: 409 });
    let kpi = await client.getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-00001' });
    expect(kpi.body.data).toMatchObject({ total_new_families: 1, informed_new_families: 0, informed_new_percentage: 0 });
    const ficha = await client.getFamilia({ familyId: 'FAM-SIM-E3-00101' });
    await client.createConversacion({
      familyId: 'FAM-SIM-E3-00101',
      body: conversationRequest({ benefit_ids: ficha.body.data.top_opportunities.map((o) => o.benefit_id) }),
      idempotencyKey: OTHER_KEY,
    });
    kpi = await client.getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-00001' });
    expect(kpi.body.data).toMatchObject({ total_new_families: 1, informed_new_families: 1, informed_new_percentage: 100, informed_families: 2 });
    await expect(client.createPreevaluacion({ body: preevaluationRequest({ commune_id: 'COM-002' }), idempotencyKey: '1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed' })).rejects.toMatchObject({ status: 422 });
  });

  it('canonicalJson ordena claves', () => {
    expect(canonicalJson({ b: 1, a: [{ d: 2, c: 3 }] })).toBe('{"a":[{"c":3,"d":2}],"b":1}');
  });
});

describe('mock-servidor — escenarios', () => {
  it('parseScenario: desconocido → default; se lee una sola vez; slow = 2 s', () => {
    expect(parseScenario('?mock=conv409')).toBe('conv409');
    expect(parseScenario('?mock=nope')).toBe('default');
    expect(parseScenario('')).toBe('default');
    resetScenarioForTests();
    expect(readScenarioOnce('?mock=kpiNull')).toBe('kpiNull');
    expect(readScenarioOnce('?mock=conv409')).toBe('kpiNull');
    resetScenarioForTests();
    expect(scenarioLatency('slow')).toBe(2000);
    expect(scenarioLatency('default')).toBe(120);
  });

  it.each([
    ['conv409', 409],
    ['conv401', 401],
    ['conv503', 503],
    ['gateway429', 429],
  ] as const)('%s → createConversacion %i', async (scenario, status) => {
    mockServer.setScenario(scenario);
    await expect(client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest(), idempotencyKey: OTHER_KEY })).rejects.toMatchObject({ kind: 'http', status });
  });

  it('html403 → 403 UNKNOWN en la ficha; error503 → 503 en la lista; empty → lista vacía', async () => {
    mockServer.setScenario('html403');
    await expect(client.getFamilia({ familyId: 'FAM-SIM-E3-00001' })).rejects.toMatchObject({ status: 403, code: 'UNKNOWN' });
    mockServer.setScenario('error503');
    await expect(client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001' })).rejects.toMatchObject({ status: 503, retryable: true });
    mockServer.setScenario('empty');
    await expect(client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001' })).resolves.toMatchObject({ body: { items: [], next_cursor: null } });
  });

  it('providerTemplate, adversarialCard, invalidCitation, assistantDeterministic, kpiSuppressed, kpiNull', async () => {
    const ids = { familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001'] } };
    mockServer.setScenario('providerTemplate');
    expect((await client.createGuion(ids)).body.provider).toBe('PLANTILLA');
    expect((await client.askCatalogAssistant({ body: { question: '¿Qué apoyos hay?' } })).body.provider).toBe('PLANTILLA');
    mockServer.setScenario('adversarialCard');
    expect((await client.createMensaje(ids)).body.content.printable_card.title).toBe('<script>alert(1)</script>');
    mockServer.setScenario('invalidCitation');
    await expect(client.createMensaje(ids)).rejects.toMatchObject({ kind: 'contract', reason: 'schema' });
    mockServer.setScenario('assistantDeterministic');
    expect((await client.askCatalogAssistant({ body: { question: '¿Qué apoyos hay?' } })).body.intent).toBe('REQUIRES_DETERMINISTIC_EVALUATION');
    mockServer.setScenario('kpiSuppressed');
    expect((await client.getKpi({ nivel: 'comuna', id: 'COM-001' })).body.data).toMatchObject({ suppressed: true, level: 'comuna', scope_id: 'COM-001' });
    mockServer.setScenario('kpiNull');
    expect((await client.getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-00002' })).body.data).toMatchObject({ informed_percentage: null, opportunity_coverage_percentage: null });
  });

  it('snapshotChange: tras la primera respuesta el servidor publica otro snapshot; snapshotPageChange solo en la página 2', async () => {
    mockServer.setScenario('snapshotChange');
    expect((await client.listJardines()).body.meta.snapshot_id).toBe('SNAP-SIM-DEMO-001');
    expect((await client.listJardines()).body.meta.snapshot_id).toBe(NEXT_SNAPSHOT);
    mockServer.reset();
    mockServer.setScenario('snapshotPageChange');
    const page1 = await client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001' });
    const page2 = await client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001', cursor: page1.body.next_cursor ?? '' });
    expect(page1.body.meta.snapshot_id).toBe('SNAP-SIM-DEMO-001');
    expect(page2.body.meta.snapshot_id).toBe(NEXT_SNAPSHOT);
  });

  it('preevalTimeout: el primer envío se registra pero la respuesta se pierde; el reintento con la misma clave devuelve la misma familia', async () => {
    mockServer.setScenario('preevalTimeout');
    await expect(client.createPreevaluacion({ body: preevaluationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY })).rejects.toMatchObject({ kind: 'network' });
    expect(mockServer.snapshotOfState().newFamilies).toBe(1);
    const retry = await client.createPreevaluacion({ body: preevaluationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY });
    expect(retry.body.data.family_id).toBe('FAM-SIM-E3-00101');
    expect(mockServer.snapshotOfState().newFamilies).toBe(1);
  });
});

describe('transporte mock en proceso', () => {
  afterEach(() => vi.restoreAllMocks());

  it('NIT 12: sin handler → contract(unexpected_status) + log.warn mock_unhandled', async () => {
    const warn = vi.spyOn(log, 'warn');
    setTransport(createMockTransport({ handlers: [], session: createSession(createNoneAdapter()), baseUrl: TEST_API_BASE, isOnline: () => true }));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'unexpected_status' });
    expect(warn).toHaveBeenCalledWith({ op: 'listJardines', kind: 'mock_unhandled' });
  });

  it('navigator.onLine === false → TypeError → network, sin consultar handlers', async () => {
    const isolated = createMockServer();
    setTransport(createMockTransport({ handlers: isolated.handlers, session: createSession(createNoneAdapter()), baseUrl: TEST_API_BASE, isOnline: () => false }));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'network' });
  });

  it('latencia simulada abortable y misma puerta de sesión', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    const session = createSession(createNoneAdapter());
    setTransport(createMockTransport({ handlers: mockServer.handlers, session, baseUrl: TEST_API_BASE, latencyMs: 2000, isOnline: () => true }));
    const pending = client.listJardines().catch((e: unknown) => e);
    session.abortSignal();
    await expect(pending).resolves.toMatchObject({ kind: 'cancelled', cause: 'session' });
    vi.useRealTimers();
  });

  it('startBrowserMocks lee el escenario y usa su latencia', async () => {
    resetScenarioForTests();
    const mocks = startBrowserMocks({ session: createSession(createNoneAdapter()), baseUrl: TEST_API_BASE, search: '?mock=kpiNull' });
    expect(mocks.scenario).toBe('kpiNull');
    expect(mocks.server.scenario()).toBe('kpiNull');
    resetScenarioForTests();
    // No hay requests reales: setupServer sigue activo con onUnhandledFrame: 'error'.
    expect(server.listHandlers().length).toBeGreaterThan(0);
  });
});
