// Contrato del cliente C3 (design.md §6.2–§6.4, fila `api/client.contract.test.ts` de §19).
// Integración con setupServer (fetch real interceptado) + fetch simulado para casos byte a byte.
import { HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AuthAdapter } from '../auth/adapter';
import { createNoneAdapter } from '../auth/none';
import { createSession, type Session } from '../auth/session';
import { conversationRequest, payloadOf, preevaluationRequest, variants } from '../test/fixtures';
import { server, TEST_API_BASE } from '../test/mswServer';
import { expectedStatusOf, OPERATION_CALLS, OPERATION_IDS, overrideOperation, TEST_IDEMPOTENCY_KEY } from '../test/operations';
import * as client from './client';
import { ApiError, isApiError, isInvalidResponse, isUnexpectedStatus } from './errors';
import { validateFamiliaDetailEnvelope } from './generated/validators.gen.js';
import { createFetchTransport, setTransport, type TransportRequest } from './transport';
import type { OperationId } from './types';

function noneSession(): Session {
  return createSession(createNoneAdapter());
}

function cognitoSession(): Session {
  const adapter: AuthAdapter = {
    mode: 'cognito',
    init: async () => {},
    getUser: async () => null,
    signinCallback: async () => {
      throw new Error('no');
    },
    signinRedirect: async () => {},
    removeUser: async () => {},
    onAccessTokenExpired: () => () => {},
    logoutUrl: () => null,
  };
  return createSession(adapter);
}

function useFetchTransport(session: Session = noneSession(), fetchImpl?: typeof fetch): Session {
  setTransport(createFetchTransport({ baseUrl: TEST_API_BASE, session, ...(fetchImpl ? { fetchImpl } : {}) }));
  return session;
}

function stub(response: Response | ((request: Request) => Promise<Response>)): typeof fetch {
  return (async (input: RequestInfo | URL) => {
    if (typeof response === 'function') return response(input as Request);
    return response;
  }) as typeof fetch;
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (isApiError(error)) return error;
    throw error;
  }
  throw new Error('se esperaba un rechazo');
}

const jsonHeaders = { 'Content-Type': 'application/json' };

describe('client C3 — 12 operaciones con éxito (setupServer)', () => {
  beforeEach(() => {
    useFetchTransport();
  });

  it.each(OPERATION_IDS)('%s → C3Ok validado con requestId', async (operationId) => {
    const result = await OPERATION_CALLS[operationId]();
    expect(result.status).toBe(expectedStatusOf(operationId));
    expect(typeof result.requestId).toBe('string');
    expect(Number.isNaN(Date.parse(result.receivedAt))).toBe(false);
  });

  it('listJardines pide limit=100 (NIT 9) y propaga el cursor', async () => {
    const spy = vi.spyOn(globalThis, 'fetch');
    await client.listJardines();
    const request = spy.mock.calls[0]?.[0] as Request;
    expect(new URL(request.url).searchParams.get('limit')).toBe('100');
    spy.mockRestore();
    const page2 = await client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001', cursor: 'CURSOR-SIM-JAR1-P2' });
    expect(page2.body.items.map((f) => f.family_id)).toEqual(['FAM-SIM-E3-00007', 'FAM-SIM-E3-00008', 'FAM-SIM-E3-00004']);
  });
});

describe('client C3 — errores HTTP → ApiError con requestId (por status, en cualquier ruta)', () => {
  beforeEach(() => {
    useFetchTransport();
  });

  const STATUSES = [401, 403, 404, 409, 422, 429, 503] as const;
  it.each(STATUSES.map((status, i) => [status, OPERATION_IDS[(i * 5) % OPERATION_IDS.length] as OperationId] as const))(
    '%i en %s',
    async (status, operationId) => {
      const body = payloadOf<{ error: { message: string; retryable: boolean } }>(`error.${status}`);
      server.use(overrideOperation(operationId, () => HttpResponse.json(body, { status })));
      const error = await rejection(OPERATION_CALLS[operationId]());
      expect(error).toMatchObject({ kind: 'http', status, requestId: `REQ-SIM-ERR-${status}`, retryable: body.error.retryable });
      // El message del servidor nunca se guarda en el error (FE-005).
      expect(JSON.stringify(error)).not.toContain(body.error.message);
      expect(error.message).toBe('api_error:http');
    },
  );
});

describe('client C3 — respuestas que no cumplen C3 → contract(schema)', () => {
  beforeEach(() => {
    useFetchTransport();
  });

  const cases: [string, OperationId, () => unknown, number?][] = [
    ['propiedad extra', 'listJardines', variants.jardinesWithExtraProperty],
    ['enum inválido', 'listFamiliasByJardin', variants.familiasWithInvalidEnum],
    ['SI + level null', 'listOportunidades', variants.opportunitiesWithSiAndNullLevel],
    ['cita http://', 'createMensaje', variants.messageWithHttpCitation],
    ['cita javascript:', 'createMensaje', variants.messageWithJavascriptCitation],
    ['propiedad html en la tarjeta', 'createMensaje', variants.messageWithHtmlProperty],
    ['4 secciones', 'createMensaje', variants.messageWithFourSections],
    ['format_version distinto', 'createMensaje', variants.messageWithWrongFormatVersion],
    ['201 inválido', 'createConversacion', () => ({ meta: payloadOf<{ meta: unknown }>('createConversacion').meta, data: {} }), 201],
  ];

  it.each(cases)('%s', async (_name, operationId, makeBody, status = 200) => {
    server.use(overrideOperation(operationId, () => HttpResponse.json(makeBody() as Record<string, unknown>, { status })));
    const error = await rejection(OPERATION_CALLS[operationId]());
    expect(error).toMatchObject({ kind: 'contract', operationId, reason: 'schema' });
    expect(isInvalidResponse(error)).toBe(true);
    if (error.kind === 'contract') expect(typeof error.keyword).toBe('string');
    // El error no contiene valores del cuerpo.
    expect(JSON.stringify(error)).not.toMatch(/fuentes|alert|ROJO|<b>/);
  });
});

describe('client C3 — parámetros y requests inválidos se rechazan SIN fetch', () => {
  let spy: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    useFetchTransport();
    spy = vi.spyOn(globalThis, 'fetch');
  });
  afterEach(() => spy.mockRestore());

  const invalid: [string, () => Promise<unknown>][] = [
    ['ID con barra', () => client.getFamilia({ familyId: '../FAM-SIM-E3-00001' })],
    ['ID en minúsculas', () => client.getContextoFamilia({ familyId: 'fam-sim-1' })],
    ['ID > 80', () => client.listFamiliasByJardin({ gardenId: 'J'.repeat(81) })],
    ['orden desconocido', () => client.listOportunidades({ familyId: 'FAM-SIM-E3-00001', orden: 'azar' as 'prioridad' })],
    ['cursor vacío', () => client.listJardines({ cursor: '' })],
    ['guion con extra', () => client.createGuion({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001'], prompt: 'x' } as never })],
    ['guion con 4 beneficios', () => client.createMensaje({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['A', 'B', 'C', 'D'] } })],
    ['conversación con texto libre', () => client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: { ...conversationRequest(), note: 'x' } as never, idempotencyKey: TEST_IDEMPOTENCY_KEY })],
    ['conversación con clave no uuid', () => client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest(), idempotencyKey: 'clave' })],
    ['preevaluación con nombre', () => client.createPreevaluacion({ body: { ...preevaluationRequest(), name: 'x' } as never, idempotencyKey: TEST_IDEMPOTENCY_KEY })],
    ['preevaluación con fecha imposible', () => client.createPreevaluacion({ body: preevaluationRequest({ last_child_health_control_date: '2026-02-30' }), idempotencyKey: TEST_IDEMPOTENCY_KEY })],
    ['asistente vacío', () => client.askCatalogAssistant({ body: { question: '' } })],
    ['asistente con extra', () => client.askCatalogAssistant({ body: { question: 'hola', context: {} } as never })],
    ['afiche con url', () => client.ingestSyntheticFlyer({ body: { synthetic_asset_id: 'ASSET-SIM-001', media_type: 'image/png', sha256: 'a'.repeat(64), url: 'https://x.example' } as never })],
    ['kpi nivel inválido', () => client.getKpi({ nivel: 'pais' as 'nacional' })],
    ['kpi fecha inválida', () => client.getKpi({ nivel: 'nacional', desde: '2026-13-01' })],
  ];

  it.each(invalid)('%s → contract(invalid_param)', async (_name, call) => {
    const error = await rejection(call());
    expect(error).toMatchObject({ kind: 'contract', reason: 'invalid_param' });
    expect(spy).not.toHaveBeenCalled();
  });
});

describe('client C3 — opciones de fetch, headers e Idempotency-Key', () => {
  it('credentials omit, cache no-store, no-referrer, redirect manual, Accept JSON; sin Authorization en modo none', async () => {
    useFetchTransport();
    const spy = vi.spyOn(globalThis, 'fetch');
    await client.getFamilia({ familyId: 'FAM-SIM-E3-00001' });
    await client.createGuion({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001'] } });
    const [get, post] = spy.mock.calls.map((call) => call[0] as Request);
    for (const request of [get, post] as Request[]) {
      expect(request.credentials).toBe('omit');
      expect(request.cache).toBe('no-store');
      expect(request.referrerPolicy).toBe('no-referrer');
      expect(request.redirect).toBe('manual');
      expect(request.headers.get('Accept')).toBe('application/json');
      expect(request.headers.has('Authorization')).toBe(false);
      expect(request.headers.has('Cookie')).toBe(false);
    }
    expect(get?.headers.has('Content-Type')).toBe(false);
    expect(post?.headers.get('Content-Type')).toBe('application/json');
    spy.mockRestore();
  });

  it('Idempotency-Key UUID en createConversacion y createPreevaluacion', async () => {
    useFetchTransport();
    const spy = vi.spyOn(globalThis, 'fetch');
    await OPERATION_CALLS.createConversacion();
    await OPERATION_CALLS.createPreevaluacion();
    const keys = spy.mock.calls.map((call) => (call[0] as Request).headers.get('Idempotency-Key'));
    expect(keys).toEqual([TEST_IDEMPOTENCY_KEY, TEST_IDEMPOTENCY_KEY]);
    spy.mockRestore();
  });

  it('las mutations no aceptan señal del llamador (NIT 8)', () => {
    for (const fn of [client.createGuion, client.createMensaje, client.createConversacion, client.createPreevaluacion, client.askCatalogAssistant, client.ingestSyntheticFlyer]) {
      expect(fn.length).toBe(1);
    }
  });
});

describe('client C3 — puerta de sesión (Authorization solo con sesión)', () => {
  it('cognito authenticated → Bearer; anonymous → auth_required sin fetch', async () => {
    const session = useFetchTransport(cognitoSession());
    const spy = vi.spyOn(globalThis, 'fetch');
    const denied = await rejection(client.listJardines());
    expect(denied).toMatchObject({ kind: 'auth_required' });
    expect(spy).not.toHaveBeenCalled();

    session.setAuthenticated({ accessToken: 'tok-sim-contract', expiresAt: null });
    await client.listJardines();
    expect((spy.mock.calls[0]?.[0] as Request).headers.get('Authorization')).toBe('Bearer tok-sim-contract');

    session.toAnonymous('expired');
    spy.mockClear();
    await expect(client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY })).rejects.toMatchObject({ kind: 'auth_required' });
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe('client C3 — algoritmo normativo de respuesta (§6.2)', () => {
  const okJardines = () => JSON.stringify(payloadOf('listJardines'));

  it('application/json; charset=utf-8 se acepta', async () => {
    useFetchTransport(noneSession(), stub(new Response(okJardines(), { status: 200, headers: { 'Content-Type': 'Application/JSON; charset=utf-8' } })));
    await expect(client.listJardines()).resolves.toMatchObject({ status: 200, requestId: 'REQ-SIM-0001' });
  });

  it('text/plain con 200 → contract(content_type)', async () => {
    useFetchTransport(noneSession(), stub(new Response(okJardines(), { status: 200, headers: { 'Content-Type': 'text/plain' } })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'content_type' });
  });

  it('Content-Length > 1 MiB → too_large sin leer el cuerpo', async () => {
    let pulled = false;
    const body = new ReadableStream<Uint8Array>(
      {
        pull(controller) {
          pulled = true;
          controller.enqueue(new TextEncoder().encode('{}'));
          controller.close();
        },
      },
      { highWaterMark: 0 },
    );
    const response = new Response(body, { status: 200, headers: { 'Content-Type': 'application/json', 'Content-Length': '2000000' } });
    useFetchTransport(noneSession(), stub(response));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'too_large' });
    expect(pulled).toBe(false);
  });

  it('cuerpo de 1 048 577 bytes multibyte → too_large; 1 048 576 bytes pasa el tope (y falla schema)', async () => {
    const big = `{"a":"x${'ñ'.repeat(524_284)}"}`;
    expect(new TextEncoder().encode(big).byteLength).toBe(1_048_577);
    useFetchTransport(noneSession(), stub(new Response(big, { status: 200, headers: jsonHeaders })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'too_large' });

    const exact = `{"a":"${'ñ'.repeat(524_284)}"}`;
    expect(new TextEncoder().encode(exact).byteLength).toBe(1_048_576);
    useFetchTransport(noneSession(), stub(new Response(exact, { status: 200, headers: jsonHeaders })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'schema' });
  });

  it('UTF-8 inválido → encoding', async () => {
    useFetchTransport(noneSession(), stub(new Response(new Uint8Array([0x7b, 0x22, 0xff, 0x22, 0x7d]), { status: 200, headers: jsonHeaders })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'encoding' });
  });

  it('403 text/html (WAF) → http 403 UNKNOWN sin requestId, nunca ContractError', async () => {
    useFetchTransport(noneSession(), stub(new Response('<html><body>Forbidden</body></html>', { status: 403, headers: { 'Content-Type': 'text/html' } })));
    await expect(client.getFamilia({ familyId: 'FAM-SIM-E3-00001' })).rejects.toMatchObject({
      kind: 'http',
      status: 403,
      code: 'UNKNOWN',
      requestId: null,
      retryable: false,
    });
  });

  it('503 HTML → http 503 retryable', async () => {
    useFetchTransport(noneSession(), stub(new Response('<html>503</html>', { status: 503, headers: { 'Content-Type': 'text/html' } })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'http', status: 503, code: 'UNKNOWN', retryable: true });
  });

  it('429 de API Gateway {"message": …} → http 429 UNKNOWN retryable', async () => {
    useFetchTransport(noneSession(), stub(new Response('{"message":"Too Many Requests"}', { status: 429, headers: jsonHeaders })));
    await expect(OPERATION_CALLS.createConversacion()).rejects.toMatchObject({ kind: 'http', status: 429, code: 'UNKNOWN', requestId: null, retryable: true });
  });

  it('ErrorResponse > 64 KiB → UNKNOWN', async () => {
    const huge = payloadOf<{ error: { details: unknown[] } }>('error.409');
    const padded = `${JSON.stringify(huge)}${' '.repeat(70_000)}`;
    useFetchTransport(noneSession(), stub(new Response(padded, { status: 409, headers: jsonHeaders })));
    await expect(client.getFamilia({ familyId: 'FAM-SIM-E3-00001' })).rejects.toMatchObject({ kind: 'http', status: 409, code: 'UNKNOWN', requestId: null });
  });

  it('200 en createConversacion (espera 201) → unexpected_status', async () => {
    useFetchTransport(noneSession(), stub(new Response(JSON.stringify(payloadOf('createConversacion')), { status: 200, headers: jsonHeaders })));
    const error = await rejection(OPERATION_CALLS.createConversacion());
    expect(error).toMatchObject({ kind: 'contract', reason: 'unexpected_status', status: 200 });
    expect(isUnexpectedStatus(error)).toBe(true);
  });

  it('204 en una lectura → unexpected_status', async () => {
    useFetchTransport(noneSession(), stub(new Response(null, { status: 204 })));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'unexpected_status' });
  });

  it('opaqueredirect → unexpected_status', async () => {
    const opaque = { type: 'opaqueredirect', status: 0, headers: new Headers(), body: null } as unknown as Response;
    useFetchTransport(noneSession(), stub(opaque));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'contract', reason: 'unexpected_status' });
  });

  it('405 → http 405 clasificado como status inesperado', async () => {
    useFetchTransport(noneSession(), stub(new Response('', { status: 405 })));
    const error = await rejection(client.listJardines());
    expect(error).toMatchObject({ kind: 'http', status: 405, code: 'UNKNOWN' });
    expect(isUnexpectedStatus(error)).toBe(true);
    expect(isUnexpectedStatus(new ApiError({ kind: 'http', status: 404, code: 'NOT_FOUND', requestId: null, retryable: false }))).toBe(false);
  });
});

describe('client C3 — red, timeout y cancelación', () => {
  afterEach(() => vi.useRealTimers());

  const hanging = stub(
    (request) =>
      new Promise<Response>((_, reject) => {
        request.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
      }),
  );

  it('TypeError de fetch (incluye CORS bloqueado) → network', async () => {
    useFetchTransport(noneSession(), stub(async () => {
      throw new TypeError('Failed to fetch');
    }));
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'network' });
  });

  it('timeouts de la tabla §6.2: 15 s lecturas y conversación, 30 s generación/preevaluación/asistente/afiche', async () => {
    const captured: TransportRequest<unknown>[] = [];
    setTransport({
      send: async (request) => {
        captured.push(request as TransportRequest<unknown>);
        throw new ApiError({ kind: 'network' });
      },
    });
    for (const operationId of OPERATION_IDS) await OPERATION_CALLS[operationId]().catch(() => undefined);
    const byOp = Object.fromEntries(captured.map((r) => [r.operationId, r]));
    for (const op of ['listJardines', 'listFamiliasByJardin', 'getFamilia', 'getContextoFamilia', 'listOportunidades', 'getKpi', 'createConversacion']) {
      expect(byOp[op]?.timeoutMs, op).toBe(15_000);
    }
    for (const op of ['createGuion', 'createMensaje', 'createPreevaluacion', 'askCatalogAssistant', 'ingestSyntheticFlyer']) {
      expect(byOp[op]?.timeoutMs, op).toBe(30_000);
      // NIT 8: las mutations no llevan señal del llamador.
      expect(byOp[op]?.signal, op).toBeUndefined();
    }
    expect(byOp.createConversacion?.signal).toBeUndefined();
    expect(byOp.createConversacion?.expectedStatus).toBe(201);
    expect(client.OPERATION_TIMEOUTS.getFamilia).toBe(15_000);
  });

  it('al vencer el timeout del request → timeout (no cancelled)', async () => {
    const session = noneSession();
    const transport = createFetchTransport({ baseUrl: TEST_API_BASE, session, fetchImpl: hanging });
    await expect(
      transport.send({
        operationId: 'getFamilia',
        method: 'GET',
        path: '/familias/FAM-SIM-E3-00001',
        route: '/familias/{id}',
        expectedStatus: 200,
        validate: validateFamiliaDetailEnvelope,
        timeoutMs: 20,
      }),
    ).rejects.toMatchObject({ kind: 'timeout' });
  });

  it('abort del llamador → cancelled(caller); abort de sesión → cancelled(session)', async () => {
    const session = useFetchTransport(noneSession(), hanging);
    const controller = new AbortController();
    const byCaller = client.listJardines({}, { signal: controller.signal });
    controller.abort();
    await expect(byCaller).rejects.toMatchObject({ kind: 'cancelled', cause: 'caller' });

    const bySession = client.createGuion({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001'] } });
    session.abortSignal();
    await expect(bySession).rejects.toMatchObject({ kind: 'cancelled', cause: 'session' });
    // Con la señal de sesión abortada (logout en curso) no se emite el request.
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'cancelled', cause: 'session' });
  });

  it('sin transporte instalado → config', async () => {
    setTransport(null);
    await expect(client.listJardines()).rejects.toMatchObject({ kind: 'config' });
  });
});
