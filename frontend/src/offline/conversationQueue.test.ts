// Cola Demo: manejo básico de 201/409/401/503 al volver la red y borrado en logout.
// Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { AuthAdapter } from '../auth/adapter';
import { createSession } from '../auth/session';
import { uuid } from '../lib/uuid';
import { conversationRequest } from '../test/fixtures';
import { mockServer } from '../test/mswServer';
import { installTestRuntime, resetTestRuntime } from '../test/runtime';
import { drain, enqueue, listQueue } from './conversationQueue';
import { clearDemoData } from './db';

const FAMILY = 'FAM-SIM-E3-00001';
const GARDEN = 'JAR-SIM-E3-00001';

async function enqueueOne(): Promise<void> {
  const { persisted } = await enqueue({ familyId: FAMILY, gardenId: GARDEN, body: conversationRequest(), idempotencyKey: uuid() });
  expect(persisted).toBe(true);
}

function cognitoSession() {
  const adapter: AuthAdapter = {
    mode: 'cognito',
    init: async () => {},
    getUser: async () => null,
    signinCallback: async () => {
      throw new Error('sin_callback');
    },
    signinRedirect: async () => {},
    removeUser: async () => {},
    onAccessTokenExpired: () => () => {},
    logoutUrl: () => null,
  };
  const session = createSession(adapter);
  session.setAuthenticated({ accessToken: 'token-sintetico', expiresAt: null });
  return session;
}

describe('cola de conversaciones Demo', () => {
  beforeEach(async () => {
    installTestRuntime({ persistence: true });
    await clearDemoData();
  });
  afterEach(async () => {
    await clearDemoData();
    resetTestRuntime();
  });

  it('201 confirma y vacía la cola', async () => {
    await enqueueOne();
    expect(await drain()).toEqual({ confirmed: 1 });
    expect(await listQueue()).toEqual([]);
  });

  it.each([
    ['conv409', 'CONFLICTO', 409],
    ['conv503', 'REINTENTO_MANUAL', 503],
  ] as const)('%s deja la entrada en %s', async (scenario, status, httpStatus) => {
    mockServer.setScenario(scenario);
    await enqueueOne();
    expect(await drain()).toEqual({ confirmed: 0 });
    const [entry] = await listQueue();
    expect(entry?.status).toBe(status);
    expect(entry?.last_http_status).toBe(httpStatus);
  });

  it('401 con Cognito pausa la entrada y deja la sesión anónima', async () => {
    resetTestRuntime();
    const session = cognitoSession();
    installTestRuntime({ persistence: true, session });
    mockServer.setScenario('conv401');
    await enqueueOne();
    await drain();
    const [entry] = await listQueue();
    expect(entry?.status).toBe('PAUSADA_AUTH');
    expect(session.getState()).toEqual({ status: 'anonymous', reason: 'expired' });
  });

  it('no persiste IDs sin -SIM- y el logout borra la cola', async () => {
    const real = await enqueue({ familyId: 'FAM-E3-00001', gardenId: GARDEN, body: conversationRequest(), idempotencyKey: uuid() });
    expect(real.persisted).toBe(false);
    await enqueueOne();
    expect(await listQueue()).toHaveLength(1);
    await clearDemoData();
    expect(await listQueue()).toEqual([]);
  });
});
