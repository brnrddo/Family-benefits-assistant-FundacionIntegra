// "Cambio mock→real no altera vistas" (§8): las 12 operaciones devuelven el MISMO C3Ok.body con el
// transporte en proceso (getResponse) y con fetch + setupServer, partiendo del mismo estado.
import { describe, expect, it } from 'vitest';
import { createFetchTransport, setTransport } from '../api/transport';
import { createNoneAdapter } from '../auth/none';
import { createSession } from '../auth/session';
import { mockServer, TEST_API_BASE } from '../test/mswServer';
import { OPERATION_CALLS, OPERATION_IDS } from '../test/operations';
import { createMockTransport } from './transport';

describe('equivalencia transporte en proceso ↔ fetch + setupServer', () => {
  it.each(OPERATION_IDS)('%s', async (operationId) => {
    const session = createSession(createNoneAdapter());

    mockServer.reset();
    setTransport(createMockTransport({ handlers: mockServer.handlers, session, baseUrl: TEST_API_BASE, isOnline: () => true }));
    const inProcess = await OPERATION_CALLS[operationId]();

    mockServer.reset();
    setTransport(createFetchTransport({ baseUrl: TEST_API_BASE, session }));
    const viaFetch = await OPERATION_CALLS[operationId]();

    expect(viaFetch.status).toBe(inProcess.status);
    expect(viaFetch.requestId).toBe(inProcess.requestId);
    expect(viaFetch.body).toEqual(inProcess.body);
  });
});
