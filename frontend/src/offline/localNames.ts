// "Nombre de trato" del niño o niña (DEC-038; PRIVACIDAD_DEMO.md, clase "Local de la tía").
// La tía lo escribe y queda SOLO en este equipo (IndexedDB Demo, store `names`). Nunca viene de la
// API, nunca se envía a ella (ningún request, URL ni header), nunca va a logs, telemetría, prompts ni
// a la tarjeta/mensaje generado por la API. Solo existe con persistencia Demo (local/demo sintético):
// en `escala` la función está oculta y no se abre IndexedDB. El logout lo borra junto con la BD.
import { useSyncExternalStore } from 'react';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { nowMs } from '../lib/now';
import { openDemoDb, persistenceEnabled, type NameRecord } from './db';

export const LOCAL_NAME_MAX_LENGTH = 40;

/** Letras (con tildes), espacios, apóstrofo, punto y guion. Sin dígitos: evita RUT, teléfonos y fechas. */
const NAME_RE = /^\p{L}[\p{L}\p{M} '’.-]*$/u;

export type LocalNameIssue = 'empty' | 'too_long' | 'invalid_chars';
export type LocalNameCheck = { readonly ok: true; readonly value: string } | { readonly ok: false; readonly issue: LocalNameIssue };

/** NFC, sin espacios repetidos ni en los bordes. */
export function normalizeLocalName(raw: string): string {
  return raw.normalize('NFC').replace(/\s+/g, ' ').trim();
}

export function validateLocalName(raw: string): LocalNameCheck {
  const value = normalizeLocalName(raw);
  if (value === '') return { ok: false, issue: 'empty' };
  if ([...value].length > LOCAL_NAME_MAX_LENGTH) return { ok: false, issue: 'too_long' };
  if (!NAME_RE.test(value)) return { ok: false, issue: 'invalid_chars' };
  return { ok: true, value };
}

export function localNamesEnabled(): boolean {
  try {
    return runtimeConfig().capabilities.localNames && persistenceEnabled();
  } catch {
    return false;
  }
}

// --- Copia en memoria observable (la UI nunca lee IndexedDB directo) ---

const EMPTY: ReadonlyMap<string, string> = new Map();
let names: ReadonlyMap<string, string> = EMPTY;
const listeners = new Set<() => void>();

function emit(next: ReadonlyMap<string, string>): void {
  names = next;
  for (const listener of [...listeners]) listener();
}

function isValidRecord(record: NameRecord): boolean {
  if (record.data_classification !== SYNTHETIC_CLASSIFICATION || !isSyntheticId(record.family_id)) return false;
  const check = validateLocalName(record.name);
  return check.ok && check.value === record.name;
}

/** Carga los nombres guardados; borra registros inválidos. Sin persistencia deja el mapa vacío. */
export async function refreshLocalNames(): Promise<void> {
  if (!localNamesEnabled()) {
    emit(EMPTY);
    return;
  }
  try {
    const db = await openDemoDb();
    const next = new Map<string, string>();
    for (const record of await db.getAll('names')) {
      if (isValidRecord(record)) next.set(record.family_id, record.name);
      else await db.delete('names', record.family_id);
    }
    emit(next);
  } catch {
    emit(EMPTY);
  }
}

export type SaveNameResult = { readonly ok: true } | { readonly ok: false; readonly issue: LocalNameIssue | 'unavailable' };

export async function saveLocalName(familyId: string, raw: string): Promise<SaveNameResult> {
  const check = validateLocalName(raw);
  if (!check.ok) return check;
  if (!localNamesEnabled() || !isSyntheticId(familyId)) return { ok: false, issue: 'unavailable' };
  try {
    const db = await openDemoDb();
    await db.put('names', {
      family_id: familyId,
      name: check.value,
      updated_at: new Date(nowMs()).toISOString(),
      data_classification: SYNTHETIC_CLASSIFICATION,
    });
    await refreshLocalNames();
    return { ok: true };
  } catch {
    return { ok: false, issue: 'unavailable' };
  }
}

export async function removeLocalName(familyId: string): Promise<void> {
  if (!localNamesEnabled()) return;
  try {
    const db = await openDemoDb();
    await db.delete('names', familyId);
  } finally {
    await refreshLocalNames();
  }
}

/** Vacía la copia en memoria sin abrir IndexedDB (logout; la BD se borra completa aparte). */
export function clearLocalNamesMemory(): void {
  emit(EMPTY);
}

/** Lectura síncrona (pruebas y guardas fuera de React). */
export function currentLocalNames(): ReadonlyMap<string, string> {
  return names;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useLocalNames(): ReadonlyMap<string, string> {
  return useSyncExternalStore(subscribe, () => names, () => names);
}

// --- Guarda de salida: un texto libre (asistente) no puede llevar un nombre guardado ---

/** Minúsculas sin tildes, para comparar palabras. */
const fold = (text: string): string => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();

const MIN_TOKEN = 3;

/**
 * true si `text` contiene, como palabra completa, alguna palabra de 3+ letras de un nombre guardado.
 * Falla cerrada: preferimos bloquear de más antes que enviar un nombre a la API.
 */
export function containsLocalName(text: string, saved: ReadonlyMap<string, string> = names): boolean {
  if (saved.size === 0) return false;
  const words = new Set(fold(text).split(/[^\p{L}]+/u).filter((w) => w !== ''));
  for (const name of saved.values()) {
    for (const token of fold(name).split(/[^\p{L}]+/u)) {
      if (token.length >= MIN_TOKEN && words.has(token)) return true;
    }
  }
  return false;
}
