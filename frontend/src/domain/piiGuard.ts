// Barrera local de UX del asistente (design.md §9.8). NO anonimiza: falla cerrada ante cualquier
// coincidencia (aunque sea falso positivo). El servidor aplica su filtro y Guardrails.
export type PiiKind = 'rut' | 'phone' | 'email';

const PATTERNS: readonly (readonly [PiiKind, RegExp])[] = [
  ['rut', /\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b/u],
  ['phone', /(\+?56)?\s?9\s?\d{4}\s?\d{4}/u],
  ['email', /[^\s@]+@[^\s@]+\.[^\s@]{2,}/u],
];

/** Tipos de dato detectados; nunca devuelve el fragmento encontrado. */
export function detectPii(text: string): PiiKind[] {
  return PATTERNS.filter(([, re]) => re.test(text)).map(([kind]) => kind);
}

export function containsPii(text: string): boolean {
  return detectPii(text).length > 0;
}
