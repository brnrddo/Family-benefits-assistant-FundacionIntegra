// Patrón Id de C3 (`components/schemas/Id`): ^[A-Z0-9][A-Z0-9_-]*$, 1–80 caracteres.
export const ID_PATTERN = /^[A-Z0-9][A-Z0-9_-]*$/;
export const ID_MAX_LENGTH = 80;

export function isValidId(value: unknown): value is string {
  return typeof value === 'string' && value.length >= 1 && value.length <= ID_MAX_LENGTH && ID_PATTERN.test(value);
}

/** SUP-032: los IDs Demo de familia y jardín contienen `-SIM-` (p. ej. JAR-SIM-E3-00001). */
export function isSyntheticId(value: unknown): value is string {
  return isValidId(value) && value.includes('-SIM-');
}
