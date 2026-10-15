// Caché Demo de lecturas sintéticas con TTL (FE-006, SUP-032). Solo se escribe si el perfil lo
// permite, hay snapshot y TODO garden_id/family_id (clave y payload) es sintético (-SIM-).
// El contexto familiar (contexto:<id>) nunca se persiste. Al leer se revalida con el validador C3.
import type { SnapshotPersistence } from '../api/snapshot';
import type { ValidateFn } from '../api/generated/validators.gen.js';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { nowMs } from '../lib/now';
import { openDemoDb, persistenceEnabled } from './db';

export type CacheKey = 'jardines' | `familias:${string}` | `familia:${string}` | `oportunidades:${string}:prioridad`;

const ID_FIELDS = new Set(['family_id', 'garden_id']);
const MAX_DEPTH = 8;
const META_SNAPSHOT_KEY = 'last_snapshot_id';

/** true si cada `family_id`/`garden_id` anidado es un ID sintético. */
export function allIdsSynthetic(value: unknown, depth = 0): boolean {
  if (depth > MAX_DEPTH) return false;
  if (Array.isArray(value)) return value.every((item) => allIdsSynthetic(item, depth + 1));
  if (value === null || typeof value !== 'object') return true;
  for (const [key, child] of Object.entries(value)) {
    if (ID_FIELDS.has(key) && !isSyntheticId(child)) return false;
    if (typeof child === 'object' && !allIdsSynthetic(child, depth + 1)) return false;
  }
  return true;
}

function keyIsSynthetic(key: CacheKey): boolean {
  const ids = key.split(':').slice(1).filter((part) => part !== 'prioridad');
  return ids.every((id) => isSyntheticId(id));
}

function ttlMs(): number {
  return runtimeConfig().capabilities.cacheTtlHours * 3_600_000;
}

export async function writeCache(key: CacheKey, body: unknown, snapshotId: string | null): Promise<boolean> {
  if (!persistenceEnabled() || snapshotId === null || !keyIsSynthetic(key) || !allIdsSynthetic(body)) return false;
  try {
    const db = await openDemoDb();
    const now = nowMs();
    await db.put('cache', {
      key,
      snapshot_id: snapshotId,
      stored_at: new Date(now).toISOString(),
      expires_at: new Date(now + ttlMs()).toISOString(),
      body,
      data_classification: SYNTHETIC_CLASSIFICATION,
    });
    return true;
  } catch {
    return false; // cuota, BD no disponible o logout en curso: se sigue sin caché
  }
}

export async function readCache<T>(key: CacheKey, validate: ValidateFn<T>): Promise<{ body: T; storedAt: string } | null> {
  if (!persistenceEnabled()) return null;
  try {
    const db = await openDemoDb();
    const entry = await db.get('cache', key);
    if (entry === undefined) return null;
    const valid =
      entry.data_classification === SYNTHETIC_CLASSIFICATION &&
      Date.parse(entry.expires_at) > nowMs() &&
      allIdsSynthetic(entry.body) &&
      validate(entry.body);
    if (!valid) {
      await db.delete('cache', key);
      return null;
    }
    return { body: entry.body as T, storedAt: entry.stored_at };
  } catch {
    return null;
  }
}

/** Persistencia del snapshot conocido (api/snapshot.ts): purga entradas de otro snapshot. */
export const demoSnapshotPersistence: SnapshotPersistence = {
  async loadKnown() {
    try {
      const db = await openDemoDb();
      return (await db.get('meta', META_SNAPSHOT_KEY)) ?? null;
    } catch {
      return null;
    }
  },
  async saveKnown(snapshotId) {
    try {
      const db = await openDemoDb();
      await db.put('meta', snapshotId, META_SNAPSHOT_KEY);
    } catch {
      // sin persistencia: el snapshot vive solo en memoria
    }
  },
  async purgeOtherSnapshots(keep) {
    try {
      const db = await openDemoDb();
      const tx = db.transaction('cache', 'readwrite');
      for (const entry of await tx.store.getAll()) {
        if (entry.snapshot_id !== keep) await tx.store.delete(entry.key);
      }
      await tx.done;
    } catch {
      // nada que purgar
    }
  },
};
