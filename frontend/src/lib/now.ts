// Reloj inyectable (pruebas y e2e con reloj fijo). Ningún módulo debe llamar Date.now() directo
// cuando el valor afecta a TTL, fechas máximas o `occurred_at`.

type Clock = () => number;

const systemClock: Clock = () => Date.now();
let clock: Clock = systemClock;

export function setClock(next: Clock): void {
  clock = next;
}

export function resetClock(): void {
  clock = systemClock;
}

export function nowMs(): number {
  return clock();
}

export function now(): Date {
  return new Date(clock());
}

const pad = (value: number, size = 2): string => String(Math.trunc(Math.abs(value))).padStart(size, '0');

/** Fecha local del dispositivo `YYYY-MM-DD` (p. ej. `max` del control de salud, §9.6). */
export function todayLocalIso(date: Date = now()): string {
  return `${pad(date.getFullYear(), 4)}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** ISO 8601 local con offset (`2026-10-14T10:00:00-03:00`) para `occurred_at` (§9.4). */
export function nowIsoWithOffset(date: Date = now()): string {
  const offsetMinutes = -date.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? '+' : '-';
  const offset = `${sign}${pad(offsetMinutes / 60)}:${pad(offsetMinutes % 60)}`;
  return (
    `${todayLocalIso(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` + offset
  );
}
