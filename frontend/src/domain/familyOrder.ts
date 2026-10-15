// Orden NEUTRO de la lista del jardín (DEC-037). No es un ranking: no usa priority_score,
// vulnerability, conteos ni semáforo (FE-003 se mantiene; la prioridad familiar de §8.3 queda en el
// servidor). Primero las familias con nombre de trato local, por orden alfabético (es-CL, sin
// distinguir mayúsculas ni tildes); después las que no tienen nombre, por `family_id`.
import type { FamilySummary } from '../api/types';

const collator = new Intl.Collator('es-CL', { sensitivity: 'base', numeric: true });

const byId = (a: FamilySummary, b: FamilySummary): number => (a.family_id < b.family_id ? -1 : a.family_id > b.family_id ? 1 : 0);

export function sortFamiliesNeutral(items: readonly FamilySummary[], names: ReadonlyMap<string, string>): FamilySummary[] {
  return [...items].sort((a, b) => {
    const nameA = names.get(a.family_id);
    const nameB = names.get(b.family_id);
    if (nameA !== undefined && nameB !== undefined) return collator.compare(nameA, nameB) || byId(a, b);
    if (nameA !== undefined) return -1;
    if (nameB !== undefined) return 1;
    return byId(a, b);
  });
}
