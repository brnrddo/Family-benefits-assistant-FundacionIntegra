import { afterEach, describe, expect, it, vi } from 'vitest';
import { log, sanitizeLogFields } from './log';

describe('lib/log', () => {
  afterEach(() => vi.restoreAllMocks());

  it('solo conserva campos de la allowlist', () => {
    const dirty = {
      op: 'getFamilia',
      route: '/familias/{id}',
      status: 503,
      kind: 'http',
      requestId: 'REQ-SIM-0001',
      ms: 12,
      body: '{"question":"dato sensible"}',
      token: 'abc.def.ghi',
    } as unknown as Parameters<typeof sanitizeLogFields>[0];
    expect(sanitizeLogFields(dirty)).toEqual({
      op: 'getFamilia',
      route: '/familias/{id}',
      status: 503,
      kind: 'http',
      requestId: 'REQ-SIM-0001',
      ms: 12,
    });
  });

  it('no escribe en consola durante las pruebas (modo test)', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    log.warn({ op: 'listJardines', kind: 'network' });
    expect(warn).not.toHaveBeenCalled();
  });
});
