// Pista corta por familia (guion de demo 2026-10-16): una línea que le recuerda a la tía la historia
// de la familia y el porqué del apoyo, porque atiende a 20–30 niños. Determinista y solo con lo que
// C3 ya entrega y está permitido al LLM (LlmContextV1): composición (roles/edades), tramo RSH y el
// estado del apoyo (`access_state`, `missing_codes`). Las señales de urgencia/vulnerabilidad del
// contexto NO se usan (salud y situación sensible: fuera de LlmContextV1 y no se muestran en la ficha).
// En pantalla puede llevar el primer nombre de trato local; lo que se envía usa `who = null`.
// Sin códigos internos ni promesas: el motor decide, la pista solo recuerda. Puro: sin red ni logs.
import type { CompositionMember, Opportunity } from '../../api/types';
import { benefitName } from '../../i18n/copy';

const count = (n: number, one: string, many: string): string => `${n} ${n === 1 ? one : many}`;

/** "2 adultos y 3 niños, uno menor de 2 años" (solo roles y edades). */
export function householdPhrase(composition: readonly CompositionMember[]): string {
  const children = composition.filter((m) => m.role === 'CHILD');
  const adults = composition.length - children.length;
  const babies = children.filter((m) => m.age < 2).length;
  const parts = [
    ...(adults > 0 ? [count(adults, 'adulto', 'adultos')] : []),
    ...(children.length > 0 ? [count(children.length, 'niño o niña', 'niños')] : []),
  ];
  const base = parts.length === 0 ? 'una familia' : parts.join(' y ');
  if (babies === 0) return base;
  if (children.length === 1) return `${base} menor de 2 años`;
  return `${base}, ${babies === 1 ? 'uno menor' : `${babies} menores`} de 2 años`;
}

/** "es el paso más cercano" / "solo falta 1 dato"… según el estado que entrega C3 (sin el nombre). */
export function benefitStatus(o: Opportunity): string {
  const missing = o.missing_codes.length;
  switch (o.access_state) {
    case 'ELEGIBLE_SIN_ASIGNACION':
      return 'es el paso más cercano';
    case 'PENDIENTE_ANTECEDENTES':
    case 'INDETERMINADO':
      return missing === 0 ? 'faltan antecedentes' : `solo ${missing === 1 ? 'falta 1 dato' : `faltan ${missing} datos`}`;
    case 'GESTION_EN_CURSO':
      return 'ya está en trámite';
    case 'SIN_CUPO':
      return 'por ahora no hay cupo';
    case 'GESTION_RECHAZADA':
      return 'tuvo una gestión rechazada, conviene revisar por qué';
    case 'ASIGNADO':
      return 'ya está asignado';
  }
}

/** "Subsidio Familiar: es el paso más cercano." */
export const benefitReason = (o: Opportunity): string => `${benefitName(o.benefit_id, o.simple_title)}: ${benefitStatus(o)}.`;

/** "En la casa de Juanito viven 2 adultos y 3 niños. Tramo RSH 40." (`who = null` → sin nombre). */
export function householdLine(composition: readonly CompositionMember[], rshBand: number | null, who: string | null): string {
  const home = who === null ? 'En la casa viven' : `En la casa de ${who} viven`;
  const rsh = rshBand === null ? 'Sin tramo RSH conocido' : `Tramo RSH ${rshBand}`;
  return `${home} ${householdPhrase(composition)}. ${rsh}.`;
}

/** Pista completa (~15–25 palabras): hogar, tramo y, si hay, el porqué del apoyo. */
export function familyHint(
  composition: readonly CompositionMember[],
  rshBand: number | null,
  who: string | null,
  opportunity?: Opportunity,
): string {
  const line = householdLine(composition, rshBand, who);
  return opportunity === undefined ? line : `${line} ${benefitReason(opportunity)}`;
}

/** Primer nombre de trato local ("Juanito R." → "Juanito"), solo para pantalla. */
export const firstName = (familyId: string, names: ReadonlyMap<string, string>): string | null => {
  const first = names.get(familyId)?.split(' ')[0];
  return first === undefined || first === '' ? null : first;
};
