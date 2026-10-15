import { describe, expect, it } from 'vitest';
import { formatClp, formatDate, formatInteger, formatPercent, formatRelative, formatScore } from './format';

const NOW = Date.parse('2026-10-14T13:00:00Z');

describe('domain/format (es-CL)', () => {
  it('enteros y CLP sin decimales', () => {
    expect(formatInteger(1234567)).toBe('1.234.567');
    expect(formatClp(264000)).toBe('$264.000');
    expect(formatClp(264000.6)).toBe('$264.001');
  });

  it('porcentaje tal como viene de C3 (sin dividir)', () => {
    expect(formatPercent(25)).toMatch(/^25\s?%$/);
    expect(formatPercent(66.7)).toMatch(/^66,7\s?%$/);
    expect(formatPercent(0)).toMatch(/^0\s?%$/);
  });

  it('puntajes con 2 decimales y fechas DD-MM-YYYY', () => {
    expect(formatScore(0.456)).toBe('0,46');
    expect(formatScore(1)).toBe('1,00');
    expect(formatDate('2026-10-13')).toBe('13-10-2026');
    expect(formatDate('no-fecha')).toBe('no-fecha');
  });

  it('tiempo relativo', () => {
    expect(formatRelative('2026-10-14T12:55:00Z', NOW)).toBe('hace 5 minutos');
    expect(formatRelative('2026-10-14T10:00:00Z', NOW)).toBe('hace 3 horas');
    expect(formatRelative('2026-10-13T13:00:00Z', NOW)).toBe('ayer');
    expect(formatRelative('2026-10-14T13:00:00Z', NOW)).toBe('ahora');
    expect(formatRelative('x', NOW)).toBe('x');
  });
});
