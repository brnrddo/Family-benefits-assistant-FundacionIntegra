// Mock-servidor compartido por toda la suite: los mismos handlers sirven a `setupServer`
// (fetch real interceptado) y al transporte en proceso.
import { setupServer } from 'msw/node';
import { createMockServer } from '../mocks/handlers';

export const mockServer = createMockServer();
export const server = setupServer(...mockServer.handlers);

/** Base absoluta de la API en jsdom (origen de la página + /api/v1). */
export const TEST_API_BASE = `${globalThis.location?.origin ?? 'http://localhost:3000'}/api/v1`;
