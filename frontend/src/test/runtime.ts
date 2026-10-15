// Runtime de pruebas de vistas/datos: perfil `local` con mocks (setupServer), sesión `none` y
// transporte fetch contra TEST_API_BASE. Persistencia Demo solo si se pide (cola/caché).
import { snapshotStore } from '../api/snapshot';
import { createFetchTransport, setTransport } from '../api/transport';
import { createNoneAdapter } from '../auth/none';
import { createSession, installSession, resetSessionForTests, type Session } from '../auth/session';
import { configureRuntime, resetRuntimeForTests, resolveProfile, SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { TEST_API_BASE } from './mswServer';

export function installTestRuntime(
  options: { persistence?: boolean; session?: Session; fetchImpl?: typeof fetch } = {},
): Session {
  const result = resolveProfile(
    {
      VITE_PROFILE: 'local',
      VITE_USE_MOCKS: 'true',
      VITE_DATA_CLASSIFICATION: options.persistence === true ? SYNTHETIC_CLASSIFICATION : '',
    },
    { isSecureContext: true },
  );
  if (!result.ok) throw new Error('test_runtime_config');
  configureRuntime(result.config);
  const session = options.session ?? createSession(createNoneAdapter());
  installSession(session);
  // `fetchImpl` permite registrar cada request real del transporte (p. ej. prueba de privacidad).
  setTransport(createFetchTransport({ baseUrl: TEST_API_BASE, session, ...(options.fetchImpl ? { fetchImpl: options.fetchImpl } : {}) }));
  return session;
}

export function resetTestRuntime(): void {
  setTransport(null);
  snapshotStore.reset();
  resetSessionForTests();
  resetRuntimeForTests();
}
