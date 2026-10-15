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

export interface LocalNamesSeed {
  readonly data_classification: string;
  readonly names: readonly { readonly family_id: string; readonly name: string }[];
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
