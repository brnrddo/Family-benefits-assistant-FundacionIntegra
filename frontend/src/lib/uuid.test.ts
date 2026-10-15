import { describe, expect, it } from 'vitest';
import { formats } from '../api/contract/runtime.js';
import { uuid, uuidFromBytes } from './uuid';

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('lib/uuid', () => {
  it('con randomUUID entrega un v4 válido para el formato uuid del runtime', () => {
    const value = uuid();
    expect(value).toMatch(V4);
    expect(formats.uuid(value)).toBe(true);
  });

  it('sin randomUUID usa getRandomValues con bits de versión y variante', () => {
    const fallback = {
      getRandomValues: (array: Uint8Array) => globalThis.crypto.getRandomValues(array),
    } as unknown as Pick<Crypto, 'getRandomValues'>;
    const values = new Set<string>();
    for (let i = 0; i < 1000; i += 1) {
      const value = uuid(fallback);
      expect(value).toMatch(V4);
      expect(formats.uuid(value)).toBe(true);
      values.add(value);
    }
    expect(values.size).toBe(1000);
  });

  it('1 000 valores con randomUUID sin repetir', () => {
    const values = new Set(Array.from({ length: 1000 }, () => uuid()));
    expect(values.size).toBe(1000);
  });

  it('fija versión 4 y variante 10 aunque los bytes vengan en 0xff', () => {
    expect(uuidFromBytes(new Uint8Array(16).fill(0xff))).toBe('ffffffff-ffff-4fff-bfff-ffffffffffff');
    expect(() => uuidFromBytes(new Uint8Array(4))).toThrow('uuid_bytes');
  });
});
