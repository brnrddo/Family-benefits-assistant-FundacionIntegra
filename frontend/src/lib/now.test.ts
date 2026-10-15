import { afterEach, describe, expect, it } from 'vitest';
import { formats } from '../api/contract/runtime.js';
import { now, nowIsoWithOffset, nowMs, resetClock, setClock, todayLocalIso } from './now';

describe('lib/now', () => {
  afterEach(() => resetClock());

  it('usa el reloj inyectado', () => {
    const fixed = Date.parse('2026-10-14T13:00:00Z');
    setClock(() => fixed);
    expect(nowMs()).toBe(fixed);
    expect(now().toISOString()).toBe('2026-10-14T13:00:00.000Z');
  });

  it('produce fecha local YYYY-MM-DD y date-time con offset válidos para C3', () => {
    setClock(() => Date.parse('2026-10-14T13:00:00Z'));
    expect(formats.date(todayLocalIso())).toBe(true);
    const iso = nowIsoWithOffset();
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/);
    expect(formats['date-time'](iso)).toBe(true);
    expect(Date.parse(iso)).toBe(Date.parse('2026-10-14T13:00:00Z'));
  });
});
