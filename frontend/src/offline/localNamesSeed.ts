// Precarga de nombres de trato INVENTADOS para la demo (DEC-047, modifica DEC-038). Escribe directo en
// IndexedDB `names` desde un JSON local rotulado SYNTHETIC_DEMO_NOT_A_REAL_PERSON: sin red, sin API y
// sin logs. Solo siembra si el store está vacío (no pisa lo que la tía editó; tras logout o si se
// borran todos, al reabrir se vuelve a sembrar). Solo se carga con import() desde main.tsx detrás de
// `VITE_PROFILE !== 'escala'` (reemplazo estático de vite.config.ts), así el build `escala` lo excluye.
import { SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { nowMs } from '../lib/now';
import { openDemoDb } from './db';
import { cutLocalName, localNamesEnabled } from './localNames';
import seedFile from './localNamesSeed.json';

export interface DemoSessionFamily {
  readonly family_id: string;
  readonly family_name: string;
  readonly child_name: string;
}
/** Sesión demo inventada: una tía, un jardín y sus familias ficticias (SYNTHETIC_DEMO_NOT_A_REAL_PERSON). */
export interface DemoSessionSeed {
  readonly tia: { readonly tia_id: string; readonly display_name: string };
  readonly garden: { readonly garden_id: string; readonly name: string };
  readonly families: readonly DemoSessionFamily[];
}
export interface LocalNamesSeed {
  readonly data_classification: string;
  readonly names: readonly { readonly family_id: string; readonly name: string }[];
  readonly demo_session?: DemoSessionSeed;
}

/** Devuelve cuántos nombres sembró (0 si no aplica o el store ya tenía nombres). */
export async function seedLocalNames(seed: LocalNamesSeed = seedFile): Promise<number> {
  if (!localNamesEnabled() || seed.data_classification !== SYNTHETIC_CLASSIFICATION) return 0;
  const db = await openDemoDb();
  const tx = db.transaction('names', 'readwrite');
  if ((await tx.store.count()) > 0) {
    await tx.done;
    return 0;
  }
  let written = 0;
  const updatedAt = new Date(nowMs()).toISOString();
  for (const { family_id, name } of seed.names) {
    const check = cutLocalName(name);
    if (!isSyntheticId(family_id) || !check.ok || check.value !== name) continue;
    await tx.store.put({ family_id, name, updated_at: updatedAt, data_classification: SYNTHETIC_CLASSIFICATION });
    written += 1;
  }
  await tx.done;
  return written;
}
/**
 * Sesión demo: reemplaza el store `names` por los nombres de trato de las familias del jardín de la
 * sesión (mismas validaciones que `seedLocalNames`). Devuelve cuántos escribió.
 */
export async function seedDemoSessionNames(families: readonly DemoSessionFamily[]): Promise<number> {
  if (!localNamesEnabled()) return 0;
  const db = await openDemoDb();
  const tx = db.transaction('names', 'readwrite');
  await tx.store.clear();
  let written = 0;
  const updatedAt = new Date(nowMs()).toISOString();
  for (const { family_id, child_name } of families) {
    const check = cutLocalName(child_name);
    if (!isSyntheticId(family_id) || !check.ok || check.value !== child_name) continue;
    await tx.store.put({ family_id, name: child_name, updated_at: updatedAt, data_classification: SYNTHETIC_CLASSIFICATION });
    written += 1;
  }
  await tx.done;
  return written;
}
