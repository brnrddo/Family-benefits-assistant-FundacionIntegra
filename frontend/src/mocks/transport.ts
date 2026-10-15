// Transporte mock EN PROCESO (design.md §2, §6.2, NIT 12): misma interfaz, misma puerta de sesión y
// mismo algoritmo de respuesta que el transporte real, pero el `Response` sale de
// `getResponse(handlers, request)` de MSW. Sin service worker de MSW (no choca con el SW de la PWA).
import { getResponse, type RequestHandler } from 'msw';
import { contractError } from '../api/errors';
import { createTransport, type Transport } from '../api/transport';
import type { SessionPort } from '../auth/session';
import { abortableDelay, raceAbort } from '../lib/abort';
import { log } from '../lib/log';
import { createMockServer, type MockServer } from './handlers';
import { readScenarioOnce, scenarioLatency, type ScenarioId } from './scenarios';

export interface MockTransportOptions {
  readonly handlers: readonly RequestHandler[];
  readonly session: SessionPort;
  /** Base absoluta terminada en /api/v1. */
  readonly baseUrl: string;
  readonly latencyMs?: number;
  /** `navigator.onLine === false` simula red caída (pruebas y e2e). */
  readonly isOnline?: () => boolean;
}

const defaultIsOnline = (): boolean => typeof navigator === 'undefined' || navigator.onLine !== false;

export function createMockTransport(options: MockTransportOptions): Transport {
  const isOnline = options.isOnline ?? defaultIsOnline;
  const latencyMs = options.latencyMs ?? 0;
  return createTransport({
    baseUrl: options.baseUrl,
    session: options.session,
    dispatch: async (request, operationId) => {
      if (!isOnline()) throw new TypeError('Failed to fetch');
      await abortableDelay(latencyMs, request.signal);
      const response = await raceAbort(getResponse([...options.handlers], request), request.signal);
      if (response === undefined) {
        // NIT 12: ningún handler → status inesperado (y aviso en dev).
        log.warn({ op: operationId, kind: 'mock_unhandled' });
        throw contractError(operationId, 'unexpected_status');
      }
      // HttpResponse.error() del mock-servidor = respuesta perdida en la red.
      if (response.type === 'error') throw new TypeError('Failed to fetch');
      return response;
    },
  });
}

export interface BrowserMocks {
  readonly transport: Transport;
  readonly server: MockServer;
  readonly scenario: ScenarioId;
}

/** Arranque de mocks en el navegador (solo builds con VITE_USE_MOCKS=true, vía import() dinámico). */
export function startBrowserMocks(options: { session: SessionPort; baseUrl: string; search: string }): BrowserMocks {
  const scenario = readScenarioOnce(options.search);
  const server = createMockServer({ scenario });
  const transport = createMockTransport({
    handlers: server.handlers,
    session: options.session,
    baseUrl: options.baseUrl,
    latencyMs: scenarioLatency(scenario),
  });
  return { transport, server, scenario };
}
