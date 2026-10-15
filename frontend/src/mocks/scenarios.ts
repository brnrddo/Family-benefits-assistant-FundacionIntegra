// Escenarios del mock (design.md §8), leídos UNA vez de `?mock=` al iniciar (solo con mocks).
// Un valor desconocido usa `default`. Ver handlers.ts para el efecto de cada uno.
export const SCENARIO_IDS = [
  'default',
  'slow',
  'empty',
  'error503',
  'conv409',
  'conv401',
  'conv503',
  'kpiSuppressed',
  'kpiNull',
  'providerTemplate',
  'adversarialCard',
  'invalidCitation',
  'assistantDeterministic',
  'snapshotChange',
  'snapshotPageChange',
  'preevalTimeout',
  'html403',
  'gateway429',
] as const;

export type ScenarioId = (typeof SCENARIO_IDS)[number];

export const DEFAULT_LATENCY_MS = 120;
export const SLOW_LATENCY_MS = 2000;

export function isScenarioId(value: unknown): value is ScenarioId {
  return typeof value === 'string' && (SCENARIO_IDS as readonly string[]).includes(value);
}

export function parseScenario(search: string): ScenarioId {
  const value = new URLSearchParams(search).get('mock');
  return isScenarioId(value) ? value : 'default';
}

/** Latencia simulada del transporte en proceso (no aplica a setupServer en Vitest). */
export function scenarioLatency(id: ScenarioId): number {
  return id === 'slow' ? SLOW_LATENCY_MS : DEFAULT_LATENCY_MS;
}

let cached: ScenarioId | null = null;

export function readScenarioOnce(search: string): ScenarioId {
  cached ??= parseScenario(search);
  return cached;
}

export function resetScenarioForTests(): void {
  cached = null;
}
