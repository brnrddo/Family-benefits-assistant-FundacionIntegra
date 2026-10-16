// Memoria de lo que la tía ya hizo (DEC-091): "Ya le informé" / conversación registrada → la acción del
// día pasa a la siguiente familia y Inicio y el chat lo recuerdan. Vive SOLO en este equipo: copia en
// memoria observable y, con persistencia Demo, IndexedDB `actions` (el logout borra la BD y recarga).
// Solo IDs sintéticos, enums y fecha; nunca se envía a la API, logs ni prompts. Sin persistencia
// (p. ej. Escala) queda solo en memoria y se pierde al recargar.
import { useSyncExternalStore } from 'react';
import { SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { nowMs } from '../lib/now';
import { openDemoDb, persistenceEnabled, type DoneActionRecord } from './db';

export type DoneAction = Omit<DoneActionRecord, 'data_classification'>;

/** Entrada de la semilla demo: acción previa ficticia, `days_ago` días antes de entrar. */
export interface DoneActionSeed {
  readonly family_id: string;
  readonly benefit_id: string;
  readonly days_ago: number;
}

const DAY_MS = 24 * 60 * 60 * 1000;
const BENEFIT_RE = /^[A-Z0-9][A-Z0-9_-]*$/;

const EMPTY: readonly DoneAction[] = [];
let actions: readonly DoneAction[] = EMPTY;
const listeners = new Set<() => void>();

/** Una por familia (la más reciente), ordenadas de la más reciente a la más antigua. */
function emit(next: readonly DoneAction[]): void {
  const latest = new Map<string, DoneAction>();
  for (const action of next) {
    const prev = latest.get(action.family_id);
    if (prev === undefined || prev.done_at < action.done_at) latest.set(action.family_id, action);
  }
  actions = [...latest.values()].sort((a, b) => (a.done_at < b.done_at ? 1 : a.done_at > b.done_at ? -1 : 0));
  for (const listener of [...listeners]) listener();
}

function isValid(action: DoneAction): boolean {
  return (
    isSyntheticId(action.family_id) &&
    (action.benefit_id === null || BENEFIT_RE.test(action.benefit_id)) &&
    !Number.isNaN(Date.parse(action.done_at))
  );
}

const toRecord = (action: DoneAction): DoneActionRecord => ({ ...action, data_classification: SYNTHETIC_CLASSIFICATION });

/** Carga lo guardado en el equipo (arranque). Sin persistencia conserva la copia en memoria. */
export async function refreshDoneActions(): Promise<void> {
  if (!persistenceEnabled()) return;
  try {
    const db = await openDemoDb();
    const next: DoneAction[] = [];
    for (const { data_classification, ...action } of await db.getAll('actions')) {
      if (data_classification === SYNTHETIC_CLASSIFICATION && isValid(action)) next.push(action);
      else await db.delete('actions', action.family_id);
    }
    emit(next);
  } catch {
    // Sin IndexedDB: se mantiene lo que haya en memoria.
  }
}

/** "Ya hablé con esta familia" (hoy). Primero en memoria (la UI cambia al instante), luego al equipo. */
export async function recordDoneAction(familyId: string, benefitId: string | null): Promise<void> {
  const action: DoneAction = { family_id: familyId, benefit_id: benefitId, done_at: new Date(nowMs()).toISOString(), origin: 'TIA' };
  if (!isValid(action)) return;
  emit([...actions, action]);
  if (!persistenceEnabled()) return;
  try {
    await (await openDemoDb()).put('actions', toRecord(action));
  } catch {
    // Queda solo en memoria.
  }
}

/** Sesión demo: reemplaza la memoria por las acciones previas ficticias de la semilla. */
export async function seedDoneActions(seed: readonly DoneActionSeed[]): Promise<void> {
  const base = nowMs();
  const next = seed
    .map((entry): DoneAction => ({
      family_id: entry.family_id,
      benefit_id: entry.benefit_id,
      done_at: new Date(base - Math.max(0, entry.days_ago) * DAY_MS).toISOString(),
      origin: 'SIMULADO_DEMO',
    }))
    .filter(isValid);
  emit(next);
  if (!persistenceEnabled()) return;
  try {
    const db = await openDemoDb();
    const tx = db.transaction('actions', 'readwrite');
    await tx.store.clear();
    for (const action of next) await tx.store.put(toRecord(action));
    await tx.done;
  } catch {
    // Queda solo en memoria.
  }
}

/** Vacía la copia en memoria (pruebas; el logout borra la BD y recarga la app). */
export function clearDoneActionsMemory(): void {
  emit(EMPTY);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useDoneActions(): readonly DoneAction[] {
  return useSyncExternalStore(subscribe, () => actions, () => actions);
}
