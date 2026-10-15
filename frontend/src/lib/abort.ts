// Combinación de señales de aborto (§6.2): llamador + sesión + timeout.
// Usa AbortSignal.any si existe; si no, un combinador propio (celulares antiguos).

export function anySignal(signals: readonly (AbortSignal | undefined)[]): AbortSignal {
  const present = signals.filter((s): s is AbortSignal => s !== undefined);
  const native = (AbortSignal as unknown as { any?: (s: AbortSignal[]) => AbortSignal }).any;
  if (typeof native === 'function') return native.call(AbortSignal, present);
  return combine(present);
}

/** Combinador propio exportado para probarlo aunque el entorno tenga AbortSignal.any. */
export function combine(signals: readonly AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  const already = signals.find((s) => s.aborted);
  if (already !== undefined) {
    controller.abort(already.reason);
    return controller.signal;
  }
  const listeners: (() => void)[] = [];
  const cleanup = () => {
    signals.forEach((s, i) => {
      const listener = listeners[i];
      if (listener !== undefined) s.removeEventListener('abort', listener);
    });
  };
  for (const signal of signals) {
    const listener = () => {
      cleanup();
      controller.abort(signal.reason);
    };
    listeners.push(listener);
    signal.addEventListener('abort', listener, { once: true });
  }
  return controller.signal;
}

export interface TimeoutHandle {
  readonly signal: AbortSignal;
  clear(): void;
}

/** Señal de timeout propia (compatible con timers falsos de Vitest). */
export function timeoutSignal(ms: number): TimeoutHandle {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException('timeout', 'TimeoutError')), ms);
  return {
    signal: controller.signal,
    clear: () => clearTimeout(timer),
  };
}

/** Espera `ms` o rechaza si la señal se aborta (latencia simulada del mock). */
export function abortableDelay(ms: number, signal?: AbortSignal): Promise<void> {
  if (ms <= 0) {
    return signal?.aborted ? Promise.reject(abortError()) : Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError());
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(abortError());
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/** Rechaza la promesa cuando la señal se aborta (para APIs que no aceptan señal). */
export function raceAbort<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  if (signal.aborted) return Promise.reject(abortError());
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(abortError());
    signal.addEventListener('abort', onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener('abort', onAbort);
        resolve(value);
      },
      (error: unknown) => {
        signal.removeEventListener('abort', onAbort);
        reject(error);
      },
    );
  });
}

function abortError(): DOMException {
  return new DOMException('aborted', 'AbortError');
}
