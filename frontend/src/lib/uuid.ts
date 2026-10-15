// UUID v4 para Idempotency-Key (§9.4). `crypto.randomUUID` solo existe en contexto seguro;
// el respaldo arma un v4 con `crypto.getRandomValues` (disponible también fuera de él).

const HEX = Array.from({ length: 256 }, (_, i) => i.toString(16).padStart(2, '0'));

export function uuidFromBytes(bytes: Uint8Array): string {
  if (bytes.length !== 16) throw new Error('uuid_bytes');
  const b = Uint8Array.from(bytes);
  b[6] = ((b[6] ?? 0) & 0x0f) | 0x40; // versión 0100
  b[8] = ((b[8] ?? 0) & 0x3f) | 0x80; // variante 10
  const h = Array.from(b, (byte) => HEX[byte] ?? '00');
  return `${h.slice(0, 4).join('')}-${h.slice(4, 6).join('')}-${h.slice(6, 8).join('')}-${h.slice(8, 10).join('')}-${h.slice(10, 16).join('')}`;
}

export function uuid(cryptoImpl: Pick<Crypto, 'getRandomValues'> & Partial<Pick<Crypto, 'randomUUID'>> = globalThis.crypto): string {
  if (typeof cryptoImpl.randomUUID === 'function') return cryptoImpl.randomUUID();
  return uuidFromBytes(cryptoImpl.getRandomValues(new Uint8Array(16)));
}
