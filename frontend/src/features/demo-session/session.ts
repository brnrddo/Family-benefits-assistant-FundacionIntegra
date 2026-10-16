// Sesión demo "Entrar como Tía X (demo)" (plan de arreglos, decisiones 4–6). Complementa Cognito: se
// monta dentro de RequireSession. Datos 100 % inventados (SYNTHETIC_DEMO_NOT_A_REAL_PERSON) desde
// `offline/localNamesSeed.json`, cargado con import() detrás de `VITE_PROFILE !== 'escala'` para que el
// build `escala` no lo incluya. En sessionStorage solo se guarda el `tia_id` sintético; los nombres de
// trato van a IndexedDB `names` (el logout los borra).
import { useSyncExternalStore } from 'react';
import { demoSessionEnabled, runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../../config/profile';
import { log } from '../../lib/log';
import { refreshLocalNames } from '../../offline/localNames';
import type { DemoSessionSeed } from '../../offline/localNamesSeed';

const STORAGE_KEY = 'brujula.demo_session.v1';

export interface DemoFamilyEntry {
  readonly familyName: string;
  readonly childName: string;
}
export interface DemoSessionState {
  /** Semilla disponible (para la pantalla de bienvenida), aunque aún no se haya entrado. */
  readonly seed: DemoSessionSeed | null;
  readonly active: boolean;
  readonly directory: ReadonlyMap<string, DemoFamilyEntry>;
}

const EMPTY_DIRECTORY: ReadonlyMap<string, DemoFamilyEntry> = new Map();
const INITIAL: DemoSessionState = { seed: null, active: false, directory: EMPTY_DIRECTORY };
let state: DemoSessionState = INITIAL;
const listeners = new Set<() => void>();

function emit(next: DemoSessionState): void {
  state = next;
  for (const listener of [...listeners]) listener();
}

function enabled(): boolean {
  try {
    return demoSessionEnabled(runtimeConfig());
  } catch {
    return false;
  }
}

function directoryOf(seed: DemoSessionSeed): ReadonlyMap<string, DemoFamilyEntry> {
  return new Map(seed.families.map((f) => [f.family_id, { familyName: f.family_name, childName: f.child_name }]));
}

async function loadSeed(): Promise<DemoSessionSeed | null> {
  if (import.meta.env.VITE_PROFILE === 'escala') return null;
  const file = (await import('../../offline/localNamesSeed.json')).default;
  if (file.data_classification !== SYNTHETIC_CLASSIFICATION) return null;
  return file.demo_session;
}

function readStored(): string | null {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Arranque: carga la semilla y, si la pestaña ya había entrado, reactiva la sesión sin resembrar. */
export async function restoreDemoSession(): Promise<void> {
  if (!enabled()) return;
  try {
    const seed = await loadSeed();
    if (seed === null) return;
    const active = readStored() === seed.tia.tia_id;
    emit({ seed, active, directory: active ? directoryOf(seed) : EMPTY_DIRECTORY });
    if (active) await refreshLocalNames();
  } catch {
    log.warn({ kind: 'demo_session_restore_failed' });
  }
}

/** "Entrar como Tía X (demo)": siembra los nombres del jardín y activa la sesión. */
export async function enterDemoSession(): Promise<void> {
  if (!enabled()) return;
  const seed = state.seed ?? (await loadSeed());
  if (seed === null) return;
  const { seedDemoSessionNames } = await import('../../offline/localNamesSeed');
  await seedDemoSessionNames(seed.families);
  await refreshLocalNames();
  try {
    window.sessionStorage.setItem(STORAGE_KEY, seed.tia.tia_id);
  } catch {
    // Sin sessionStorage la sesión vive solo en memoria.
  }
  emit({ seed, active: true, directory: directoryOf(seed) });
}

/** Logout: olvida la sesión demo (los nombres en IndexedDB los borra performLogout). */
export function clearDemoSession(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nada que borrar.
  }
  emit({ ...state, active: false, directory: EMPTY_DIRECTORY });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useDemoSession(): DemoSessionState {
  return useSyncExternalStore(subscribe, () => state, () => state);
}

/** Directorio family_id → apellido de familia y nombre del niño (vacío sin sesión demo). */
export function useDemoDirectory(): ReadonlyMap<string, DemoFamilyEntry> {
  return useDemoSession().directory;
}

/** Solo pruebas. */
export function resetDemoSessionForTests(): void {
  emit(INITIAL);
}
