// Nombre visible de una familia (DEC-038). Solo PRESENTACIÓN: el nombre de trato es local de la tía
// y nunca sale del equipo; sin nombre se usa un genérico amable con el ID corto. La URL y todos los
// requests siguen usando el `family_id` completo de C3.
import { t } from '../i18n/copy';

/** Último tramo del ID sintético (`FAM-SIM-E3-00003` → `00003`); si no hay tramos, el ID completo. */
export function shortFamilyId(familyId: string): string {
  const parts = familyId.split('-').filter((part) => part !== '');
  return parts[parts.length - 1] ?? familyId;
}

export function familyDisplayName(familyId: string, names: ReadonlyMap<string, string>): string {
  return names.get(familyId) ?? t('family.generic_name', { short_id: shortFamilyId(familyId) });
}
