// Lectura de cuerpos con tope en BYTES UTF-8 recibidos (no caracteres) y decodificación
// estricta (§6.2, pasos 1 y 2). Nunca devuelve parte del contenido si se excede el tope.

export const MAX_SUCCESS_BODY_BYTES = 1_048_576; // 1 MiB
export const MAX_ERROR_BODY_BYTES = 65_536; // 64 KiB

export type BodyReadResult = { ok: true; text: string } | { ok: false; reason: 'too_large' | 'encoding' };

async function cancelQuietly(reader: ReadableStreamDefaultReader<Uint8Array>): Promise<void> {
  try {
    await reader.cancel();
  } catch {
    // el stream ya pudo cerrarse o abortarse
  }
}

export async function readBodyText(response: Response, maxBytes: number): Promise<BodyReadResult> {
  const chunks: Uint8Array[] = [];
  let total = 0;
  if (response.body !== null) {
    const reader = response.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await cancelQuietly(reader);
        return { ok: false, reason: 'too_large' };
      }
      chunks.push(value);
    }
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return { ok: true, text: new TextDecoder('utf-8', { fatal: true }).decode(bytes) };
  } catch {
    return { ok: false, reason: 'encoding' };
  }
}

/** Cancela el cuerpo sin leerlo (p. ej. `Content-Length` excedido). */
export async function discardBody(response: Response): Promise<void> {
  try {
    await response.body?.cancel();
  } catch {
    // ignorado: solo liberamos el recurso
  }
}
