// Formatos de presentación es-CL (§7.3). Solo FORMATEA valores que vienen de C3: no calcula
// porcentajes, montos ni puntajes (FE-003). `null` se muestra con `common.not_available` en la vista.
const LOCALE = 'es-CL';

const integerFormat = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
const clpFormat = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
// `unit: percent` formatea el número tal cual (25 → "25 %" según CLDR): no divide ni multiplica.
const percentFormat = new Intl.NumberFormat(LOCALE, { style: 'unit', unit: 'percent', maximumFractionDigits: 1 });
const scoreFormat = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const relativeFormat = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });

const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function formatInteger(value: number): string {
  return integerFormat.format(value);
}

/** Monto CLP sin decimales, p. ej. `$264.000`. */
export function formatClp(value: number): string {
  return clpFormat.format(value);
}

/** Porcentaje entregado por C3 en escala 0–100, p. ej. 66.7 → `66,7 %`. */
export function formatPercent(value: number): string {
  return percentFormat.format(value);
}

/** Puntajes U/B/V y score con 2 decimales (detalle técnico). */
export function formatScore(value: number): string {
  return scoreFormat.format(value);
}

/** Fecha C3 `YYYY-MM-DD` → `DD-MM-YYYY` sin depender de la zona horaria. */
export function formatDate(isoDate: string): string {
  const match = DATE_RE.exec(isoDate);
  if (match === null) return isoDate;
  return `${match[3]}-${match[2]}-${match[1]}`;
}

/** Fecha local de un instante (p. ej. `card_v1.printed_on`). */
export function formatLocalDate(date: Date): string {
  return new Intl.DateTimeFormat(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date);
}

const UNITS: readonly (readonly [Intl.RelativeTimeFormatUnit, number])[] = [
  ['year', 365 * 24 * 3600],
  ['month', 30 * 24 * 3600],
  ['day', 24 * 3600],
  ['hour', 3600],
  ['minute', 60],
  ['second', 1],
];

/** Tiempo relativo (`hace 5 minutos`) entre un instante ISO y `nowMs`. */
export function formatRelative(fromIso: string, nowMs: number): string {
  const from = Date.parse(fromIso);
  if (Number.isNaN(from)) return fromIso;
  const deltaSeconds = Math.round((from - nowMs) / 1000);
  const abs = Math.abs(deltaSeconds);
  for (const [unit, seconds] of UNITS) {
    if (abs >= seconds || unit === 'second') {
      return relativeFormat.format(Math.round(deltaSeconds / seconds), unit);
    }
  }
  return relativeFormat.format(0, 'second');
}
