// Cola mínima de conversaciones Demo (FE-006/FE-007, design.md §12.4 simplificado).
// Solo IDs -SIM- y cuerpos C3 válidos (enums/IDs/fecha, sin texto libre). Una conversación en
// cola NO cuenta en el KPI: solo un 201 del servidor confirma. Vaciado FIFO, de a uno, en eventos
// discretos (online, arranque, login, "Enviar ahora"); sin sincronización entre pestañas: la
// idempotencia del servidor (misma clave y cuerpo) cubre un envío doble.
import { useSyncExternalStore } from 'react';
import { createConversacion } from '../api/client';
import { isApiError } from '../api/errors';
import { validateConversationRequest } from '../api/generated/validators.gen.js';
import type { ConversationRequest } from '../api/types';
import { getSession } from '../auth/session';
import { SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { nowMs } from '../lib/now';
import { openDemoDb, persistenceEnabled, type QueueRecord, type QueueStatus } from './db';

const QUEUE_TTL_MS = 72 * 3_600_000;
const REJECTED_TTL_MS = 24 * 3_600_000;

/** Cómo tratar una falla al enviar una conversación (misma tabla para envío directo y vaciado). */
export type ConversationFailure = 'retry_later' | 'paused_auth' | 'conflict' | 'manual' | 'rejected' | 'cancelled';

export function classifyConversationError(error: unknown, authMode: 'none' | 'cognito'): ConversationFailure {
  if (!isApiError(error)) return 'manual';
  switch (error.kind) {
    case 'network':
    case 'timeout':
    case 'auth_required':
      return 'retry_later';
    case 'cancelled':
      return 'cancelled';
    case 'http':
      // Sin login posible (authMode none), un 401 no se arregla iniciando sesión (NIT 4).
      if (error.status === 401) return authMode === 'cognito' ? 'paused_auth' : 'manual';
      if (error.status === 409) return 'conflict';
      if (error.status === 429 || error.status >= 500) return 'manual';
      return 'rejected';
    case 'contract':
      // 201 con cuerpo inválido: reintento idempotente con la misma clave.
      return error.reason === 'unexpected_status' || error.reason === 'invalid_param' ? 'rejected' : 'manual';
    default:
      return 'rejected';
  }
}

const STATUS_BY_FAILURE: Readonly<Record<Exclude<ConversationFailure, 'retry_later' | 'cancelled'>, QueueStatus>> = {
  paused_auth: 'PAUSADA_AUTH',
  conflict: 'CONFLICTO',
  manual: 'REINTENTO_MANUAL',
  rejected: 'RECHAZADA',
};

export function queueStatusFor(failure: ConversationFailure): QueueStatus {
  return failure === 'retry_later' || failure === 'cancelled' ? 'EN_ESPERA' : STATUS_BY_FAILURE[failure];
}

function isPersistable(familyId: string, gardenId: string, body: unknown): body is ConversationRequest {
  return isSyntheticId(familyId) && isSyntheticId(gardenId) && validateConversationRequest(body);
}

function isValidRecord(record: QueueRecord): boolean {
  return (
    record.data_classification === SYNTHETIC_CLASSIFICATION &&
    isPersistable(record.family_id, record.garden_id, record.body) &&
    !Number.isNaN(Date.parse(record.expires_at))
  );
}

export interface EnqueueInput {
  readonly familyId: string;
  readonly gardenId: string;
  readonly body: ConversationRequest;
  readonly idempotencyKey: string;
  readonly status?: QueueStatus;
  readonly lastHttpStatus?: number | null;
}

export async function enqueue(input: EnqueueInput): Promise<{ persisted: boolean }> {
  if (!persistenceEnabled() || !isPersistable(input.familyId, input.gardenId, input.body)) return { persisted: false };
  try {
    const db = await openDemoDb();
    const now = nowMs();
    await db.put('queue', {
      idempotency_key: input.idempotencyKey,
      family_id: input.familyId,
      garden_id: input.gardenId,
      body: input.body,
      created_at: new Date(now).toISOString(),
      expires_at: new Date(now + QUEUE_TTL_MS).toISOString(),
      status: input.status ?? 'EN_ESPERA',
      last_http_status: input.lastHttpStatus ?? null,
      data_classification: SYNTHETIC_CLASSIFICATION,
    });
    return { persisted: true };
  } catch {
    return { persisted: false };
  } finally {
    await refreshQueue();
  }
}

/** Lista la cola aplicando retención: inválidas se borran; vencidas pasan a RECHAZADA y luego se borran. */
export async function listQueue(): Promise<QueueRecord[]> {
  if (!persistenceEnabled()) return [];
  const db = await openDemoDb();
  const now = nowMs();
  const kept: QueueRecord[] = [];
  for (const record of await db.getAll('queue')) {
    const expired = Date.parse(record.expires_at) <= now;
    if (!isValidRecord(record) || (expired && record.status === 'RECHAZADA')) {
      await db.delete('queue', record.idempotency_key);
      continue;
    }
    if (expired) {
      const rejected: QueueRecord = { ...record, status: 'RECHAZADA', expires_at: new Date(now + REJECTED_TTL_MS).toISOString() };
      await db.put('queue', rejected);
      kept.push(rejected);
      continue;
    }
    kept.push(record);
  }
  return kept.sort((a, b) => a.created_at.localeCompare(b.created_at));
}

async function setStatus(key: string, status: QueueStatus, httpStatus: number | null): Promise<void> {
  const db = await openDemoDb();
  const current = await db.get('queue', key);
  if (current === undefined) return; // borrada mientras tanto (logout o descarte)
  const expires = status === 'RECHAZADA' ? new Date(nowMs() + REJECTED_TTL_MS).toISOString() : current.expires_at;
  await db.put('queue', { ...current, status, last_http_status: httpStatus, expires_at: expires });
}

export async function discardEntry(key: string): Promise<void> {
  if (!persistenceEnabled()) return;
  try {
    const db = await openDemoDb();
    await db.delete('queue', key);
  } finally {
    await refreshQueue();
  }
}

let draining = false;

export interface DrainResult {
  readonly confirmed: number;
}

/**
 * Envía en orden FIFO las entradas EN_ESPERA y PAUSADA_AUTH (y REINTENTO_MANUAL si `manual`).
 * 201 borra; 409 → CONFLICTO; 401 → PAUSADA_AUTH (Cognito) y detiene; 503/429 → REINTENTO_MANUAL;
 * red/timeout/sin sesión → se detiene y la entrada sigue EN_ESPERA.
 */
export async function drain(options: { manual?: boolean } = {}): Promise<DrainResult> {
  if (draining || !persistenceEnabled()) return { confirmed: 0 };
  const session = getSession();
  const status = session.getState().status;
  if (status !== 'none' && status !== 'authenticated') return { confirmed: 0 };
  draining = true;
  let confirmed = 0;
  try {
    const sendable = (await listQueue()).filter(
      (entry) =>
        entry.status === 'EN_ESPERA' || entry.status === 'PAUSADA_AUTH' || (options.manual === true && entry.status === 'REINTENTO_MANUAL'),
    );
    for (const entry of sendable) {
      try {
        await createConversacion({ familyId: entry.family_id, body: entry.body, idempotencyKey: entry.idempotency_key });
        const db = await openDemoDb();
        await db.delete('queue', entry.idempotency_key);
        confirmed += 1;
      } catch (error) {
        const failure = classifyConversationError(error, session.authMode);
        if (failure === 'retry_later' || failure === 'cancelled') break;
        await setStatus(entry.idempotency_key, queueStatusFor(failure), isApiError(error) && error.kind === 'http' ? error.status : null);
        if (failure === 'paused_auth') {
          session.toAnonymous('expired');
          break;
        }
      }
    }
  } catch {
    // BD no disponible o logout en curso: se intentará en el próximo evento
  } finally {
    draining = false;
    await refreshQueue();
  }
  return { confirmed };
}

// --- Resumen observable para la UI (insignia en Inicio, diálogo de logout) ---

export interface QueueSummary {
  readonly entries: readonly QueueRecord[];
  /** Familias con una conversación local que aún no confirma el servidor (no RECHAZADA). */
  readonly pendingFamilyIds: ReadonlySet<string>;
}

const EMPTY_SUMMARY: QueueSummary = { entries: [], pendingFamilyIds: new Set() };
let summary: QueueSummary = EMPTY_SUMMARY;
const listeners = new Set<() => void>();

export async function refreshQueue(): Promise<void> {
  let entries: QueueRecord[] = [];
  try {
    entries = await listQueue();
  } catch {
    entries = [];
  }
  summary =
    entries.length === 0
      ? EMPTY_SUMMARY
      : { entries, pendingFamilyIds: new Set(entries.filter((e) => e.status !== 'RECHAZADA').map((e) => e.family_id)) };
  for (const listener of [...listeners]) listener();
}

/** Vacía el resumen en memoria sin abrir IndexedDB (logout). */
export function clearQueueSummary(): void {
  summary = EMPTY_SUMMARY;
  for (const listener of [...listeners]) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useQueueSummary(): QueueSummary {
  return useSyncExternalStore(subscribe, () => summary, () => summary);
}
