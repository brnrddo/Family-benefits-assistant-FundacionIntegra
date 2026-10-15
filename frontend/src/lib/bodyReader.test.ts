import { describe, expect, it } from 'vitest';
import { discardBody, readBodyText } from './bodyReader';

function streamResponse(chunks: Uint8Array[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk);
      controller.close();
    },
  });
  return new Response(stream);
}

describe('lib/bodyReader', () => {
  it('lee texto UTF-8 válido', async () => {
    await expect(readBodyText(new Response('{"a":"ñandú"}'), 1024)).resolves.toEqual({ ok: true, text: '{"a":"ñandú"}' });
  });

  it('cuenta bytes, no caracteres: 4 bytes con tope 3 → too_large', async () => {
    // "ññ" son 2 caracteres y 4 bytes UTF-8
    await expect(readBodyText(new Response('ññ'), 3)).resolves.toEqual({ ok: false, reason: 'too_large' });
    await expect(readBodyText(new Response('ññ'), 4)).resolves.toEqual({ ok: true, text: 'ññ' });
  });

  it('corta al pasar el tope aunque llegue en varios trozos', async () => {
    const chunk = new Uint8Array(600).fill(0x61);
    await expect(readBodyText(streamResponse([chunk, chunk]), 1000)).resolves.toEqual({ ok: false, reason: 'too_large' });
  });

  it('UTF-8 inválido → encoding', async () => {
    await expect(readBodyText(streamResponse([new Uint8Array([0x7b, 0xff, 0xfe, 0x7d])]), 1024)).resolves.toEqual({
      ok: false,
      reason: 'encoding',
    });
  });

  it('cuerpo vacío → texto vacío', async () => {
    await expect(readBodyText(new Response(null, { status: 204 }), 10)).resolves.toEqual({ ok: true, text: '' });
    await expect(discardBody(new Response('x'))).resolves.toBeUndefined();
  });
});
