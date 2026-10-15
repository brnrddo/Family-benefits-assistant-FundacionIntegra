// Store del snapshot C3 (design.md §6.2): `active` (visto en esta sesión) y `known` (último
// persistido en IndexedDB Demo). La persistencia y los efectos (invalidar queries, toast) se
// inyectan: hasta FEAT-002 son no-op. Escala nunca abre IndexedDB (persistence = null).
import { useSyncExternalStore } from 'react';

export interface SnapshotState {
  readonly active: string | null;
  readonly known: string | null;
}

/** Hook de persistencia (FEAT-002: meta.last_snapshot_id + purga por snapshot en offline/db.ts). */
export interface SnapshotPersistence {
  loadKnown(): Promise<string | null>;
  saveKnown(snapshotId: string): Promise<void>;
  /** Borra entradas de caché de snapshots distintos de `keep`. */
  purgeOtherSnapshots(keep: string): Promise<void>;
}

/** Efectos de un cambio de snapshot posterior al primero (FEAT-002: queryClient + toast). */
export interface SnapshotEffects {
  invalidateAll(): void;
  notifyChanged(): void;
}

export type ObserveOutcome = 'ignored' | 'first' | 'same' | 'changed';

const NOOP_EFFECTS: SnapshotEffects = { invalidateAll: () => {}, notifyChanged: () => {} };

export interface SnapshotStore {
  getState(): SnapshotState;
  subscribe(listener: () => void): () => void;
  /** Arranque: active = null; known = persistencia ?? null (Escala: null sin abrir IndexedDB). */
  init(options?: { persistence?: SnapshotPersistence | null; effects?: SnapshotEffects }): Promise<void>;
  /**
   * Registra el `meta.snapshot_id` de un envelope. Resuelve DESPUÉS de persistir `known`, para que
   * el escritor de caché lo espere antes de escribir cualquier entrada (§6.2).
   */
  observe(snapshotId: string | null | undefined): Promise<ObserveOutcome>;
  reset(): void;
}

export function createSnapshotStore(): SnapshotStore {
  let state: SnapshotState = { active: null, known: null };
  let persistence: SnapshotPersistence | null = null;
  let effects: SnapshotEffects = NOOP_EFFECTS;
  let chain: Promise<unknown> = Promise.resolve();
  const listeners = new Set<() => void>();

  const setState = (next: SnapshotState) => {
    state = next;
    for (const listener of [...listeners]) listener();
  };

  const observeNow = async (snapshotId: string): Promise<ObserveOutcome> => {
    const { active, known } = state;
    if (active === snapshotId) return 'same';
    if (active === null) {
      // Primer envelope de la sesión: purga silenciosa si el conocido es otro (sin invalidar ni toast).
      if (known !== null && known !== snapshotId) await persistence?.purgeOtherSnapshots(snapshotId);
      setState({ active: snapshotId, known: snapshotId });
      await persistence?.saveKnown(snapshotId);
      return 'first';
    }
    // Cambio posterior: purga + invalidación UNA vez por cambio + toast.
    await persistence?.purgeOtherSnapshots(snapshotId);
    setState({ active: snapshotId, known: snapshotId });
    await persistence?.saveKnown(snapshotId);
    effects.invalidateAll();
    effects.notifyChanged();
    return 'changed';
  };

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    async init(options = {}) {
      persistence = options.persistence ?? null;
      effects = options.effects ?? NOOP_EFFECTS;
      const known = persistence === null ? null : await persistence.loadKnown();
      setState({ active: null, known });
    },
    observe(snapshotId) {
      // Envelopes sin meta (AssistantEnvelope) no tocan el store.
      if (typeof snapshotId !== 'string' || snapshotId === '') return Promise.resolve('ignored');
      // Serializado: dos respuestas concurrentes con el mismo snapshot nuevo cuentan un solo cambio.
      const next = chain.then(() => observeNow(snapshotId));
      chain = next.catch(() => undefined);
      return next;
    },
    reset() {
      persistence = null;
      effects = NOOP_EFFECTS;
      chain = Promise.resolve();
      setState({ active: null, known: null });
    },
  };
}

/** Store del proceso. */
export const snapshotStore: SnapshotStore = createSnapshotStore();

export function useSnapshotState(store: SnapshotStore = snapshotStore): SnapshotState {
  return useSyncExternalStore(store.subscribe, store.getState, store.getState);
}

/** `meta.snapshot_id` de un envelope C3 o null (AssistantEnvelope no trae meta). */
export function snapshotIdOf(body: unknown): string | null {
  if (body === null || typeof body !== 'object') return null;
  const meta = (body as { meta?: { snapshot_id?: unknown } }).meta;
  return meta !== undefined && typeof meta.snapshot_id === 'string' ? meta.snapshot_id : null;
}
