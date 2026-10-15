import { afterEach, describe, expect, it, vi } from 'vitest';
import { abortableDelay, anySignal, combine, raceAbort, timeoutSignal } from './abort';

describe('lib/abort', () => {
  afterEach(() => vi.useRealTimers());

  it('anySignal aborta cuando aborta cualquiera de las señales', () => {
    const a = new AbortController();
    const b = new AbortController();
    const combined = anySignal([a.signal, undefined, b.signal]);
    expect(combined.aborted).toBe(false);
    b.abort('motivo-b');
    expect(combined.aborted).toBe(true);
  });

  it('el combinador propio propaga la primera señal y una ya abortada', () => {
    const a = new AbortController();
    const b = new AbortController();
    const combined = combine([a.signal, b.signal]);
    a.abort('primero');
    b.abort('segundo');
    expect(combined.aborted).toBe(true);
    expect(combined.reason).toBe('primero');
    const pre = new AbortController();
    pre.abort('ya');
    expect(combine([pre.signal]).aborted).toBe(true);
  });

  it('timeoutSignal aborta al vencer y clear lo cancela', () => {
    vi.useFakeTimers();
    const t = timeoutSignal(1000);
    vi.advanceTimersByTime(999);
    expect(t.signal.aborted).toBe(false);
    vi.advanceTimersByTime(1);
    expect(t.signal.aborted).toBe(true);
    const cleared = timeoutSignal(1000);
    cleared.clear();
    vi.advanceTimersByTime(2000);
    expect(cleared.signal.aborted).toBe(false);
  });

  it('abortableDelay y raceAbort rechazan al abortar', async () => {
    const controller = new AbortController();
    const delayed = abortableDelay(10_000, controller.signal);
    const raced = raceAbort(new Promise(() => {}), controller.signal);
    controller.abort();
    await expect(delayed).rejects.toMatchObject({ name: 'AbortError' });
    await expect(raced).rejects.toMatchObject({ name: 'AbortError' });
    await expect(abortableDelay(0)).resolves.toBeUndefined();
    await expect(raceAbort(Promise.resolve(1), new AbortController().signal)).resolves.toBe(1);
  });
});
