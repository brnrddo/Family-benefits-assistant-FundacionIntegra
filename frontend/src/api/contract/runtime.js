// Runtime ESM propio de los validadores Ajv standalone (DEC-031, §6.1).
// Reemplaza a ajv/dist/runtime/* y ajv-formats: así Ajv no llega al bundle.
// scripts/gen-contract.mjs usa este mismo módulo al compilar, por eso las formas coinciden.

/** Largo en code points (un par sustituto cuenta 1), igual que ajv/dist/runtime/ucs2length. */
export function ucs2length(str) {
  let length = 0;
  for (const _codePoint of str) length += 1;
  return length;
}

/** Igualdad profunda de valores JSON (para const/enum/uniqueItems). */
export function equal(a, b) {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') {
    // NaN no existe en JSON; se trata como distinto.
    return false;
  }
  const aIsArray = Array.isArray(a);
  if (aIsArray !== Array.isArray(b)) return false;
  if (aIsArray) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
      if (!equal(a[i], b[i])) return false;
    }
    return true;
  }
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  for (const key of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(b, key)) return false;
    if (!equal(a[key], b[key])) return false;
  }
  return true;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DATE_TIME_RE = /^(\d{4}-\d{2}-\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(?:[Zz]|([+-])(\d{2}):(\d{2}))$/;
const SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/;
const DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function isLeapYear(year) {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

/** `YYYY-MM-DD` con día válido del mes (2026-02-30 no pasa). */
function isDate(value) {
  const match = DATE_RE.exec(value);
  if (match === null) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1) return false;
  const max = month === 2 && isLeapYear(year) ? 29 : DAYS[month - 1];
  return day <= max;
}

/** RFC 3339 con offset obligatorio (Z o ±hh:mm). */
function isDateTime(value) {
  const match = DATE_TIME_RE.exec(value);
  if (match === null) return false;
  if (!isDate(match[1])) return false;
  const hour = Number(match[2]);
  const minute = Number(match[3]);
  const second = Number(match[4]);
  if (hour > 23 || minute > 59 || second > 59) return false;
  if (match[5] !== undefined) {
    if (Number(match[6]) > 23 || Number(match[7]) > 59) return false;
  }
  return true;
}

/** URI absoluta: esquema + `new URL` válido. */
function isUri(value) {
  if (!SCHEME_RE.test(value)) return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

function isUuid(value) {
  return UUID_RE.test(value);
}

export const formats = Object.freeze({
  uuid: isUuid,
  date: isDate,
  'date-time': isDateTime,
  uri: isUri,
});
