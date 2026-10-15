// IndexedDB Demo (design.md §12.2, versión simplificada). Único punto de apertura: falla cerrado
// si el perfil no permite persistencia (Escala o sin clasificación sintética), así Escala nunca
// abre IndexedDB. El logout borra la BD completa (caché, cola y meta).
import { deleteDB, openDB, type DBSchema, type IDBPDatabase } from 'idb';
import type { ConversationRequest } from '../api/types';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../config/profile';

export const DEMO_DB_NAME = 'brujula-demo';
const DELETE_TIMEOUT_MS = 3000;

export type QueueStatus = 'EN_ESPERA' | 'PAUSADA_AUTH' | 'CONFLICTO' | 'REINTENTO_MANUAL' | 'RECHAZADA';

export interface CacheRecord {
  readonly key: string;
  readonly snapshot_id: string;
  readonly stored_at: string;
  readonly expires_at: string;
  readonly body: unknown;
  readonly data_classification: typeof SYNTHETIC_CLASSIFICATION;
}

export interface QueueRecord {
  readonly idempotency_key: string;
  readonly family_id: string;
  readonly garden_id: string;
  /** Solo enums, IDs y fecha (C3 ConversationRequest): sin texto libre. */
  readonly body: ConversationRequest;
  readonly created_at: string;
  /** Plazo vigente: para enviar (72 h) o, si está RECHAZADA, para borrarse (24 h). */
  readonly expires_at: string;
  readonly status: QueueStatus;
  readonly last_http_status: number | null;
  readonly data_classification: typeof SYNTHETIC_CLASSIFICATION;
}

interface DemoSchema extends DBSchema {
  cache: { key: string; value: CacheRecord };
  queue: { key: string; value: QueueRecord };
  meta: { key: string; value: string };
}

export type DemoDb = IDBPDatabase<DemoSchema>;

let dbPromise: Promise<DemoDb> | null = null;

export function persistenceEnabled(): boolean {
  try {
    return runtimeConfig().capabilities.persistence;
  } catch {
    return false;
  }
}

export function openDemoDb(): Promise<DemoDb> {
  if (!persistenceEnabled()) return Promise.reject(new Error('persistence_disabled'));
  dbPromise ??= openDB<DemoSchema>(DEMO_DB_NAME, 1, {
    upgrade(db) {
      db.createObjectStore('cache', { keyPath: 'key' });
      db.createObjectStore('queue', { keyPath: 'idempotency_key' });
      db.createObjectStore('meta');
    },
    // Otra pestaña borra la BD (logout): soltar la conexión para no bloquearla.
    blocking() {
      void closeDemoDb();
    },
  }).catch((error: unknown) => {
    dbPromise = null;
    throw error;
  });
  return dbPromise;
}

async function closeDemoDb(): Promise<void> {
  const pending = dbPromise;
  dbPromise = null;
  if (pending === null) return;
  try {
    (await pending).close();
  } catch {
    // ya cerrada o nunca abrió
  }
}

/** Borra todo lo persistido en este dispositivo (logout, o arranque sin persistencia). */
export async function clearDemoData(): Promise<void> {
  await closeDemoDb();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    await Promise.race([
      deleteDB(DEMO_DB_NAME),
      new Promise<void>((resolve) => {
        timer = setTimeout(resolve, DELETE_TIMEOUT_MS);
      }),
    ]);
  } catch {
    // sin IndexedDB disponible: no hay nada que borrar
  } finally {
    clearTimeout(timer);
  }
}
