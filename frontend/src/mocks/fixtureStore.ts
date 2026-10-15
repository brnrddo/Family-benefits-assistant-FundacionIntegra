// Carga de fixtures sintéticos (design.md §8). Única fuente de datos de persona/hogar del mock;
// cada JSON tiene forma {data_classification, operationId, status, payload}.
export const SYNTHETIC_CLASSIFICATION = 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON';

export interface Fixture {
  readonly data_classification: string;
  /** operationId C3, o `*` para errores genéricos (ErrorResponse). */
  readonly operationId: string;
  readonly status: number;
  readonly payload: unknown;
}

const modules = import.meta.glob<Fixture>('./fixtures/*.json', { eager: true, import: 'default' });

/** Nombre de archivo sin `.json` → fixture. */
export const FIXTURES: Readonly<Record<string, Fixture>> = Object.freeze(
  Object.fromEntries(
    Object.entries(modules).map(([path, value]) => [path.replace(/^\.\/fixtures\//, '').replace(/\.json$/, ''), value]),
  ),
);

export function hasFixture(name: string): boolean {
  return Object.prototype.hasOwnProperty.call(FIXTURES, name);
}

export function fixture(name: string): Fixture {
  const found = FIXTURES[name];
  if (found === undefined) throw new Error(`fixture_missing:${name}`);
  return found;
}

/** Copia profunda del payload (nadie muta los JSON importados). */
export function payloadOf<T>(name: string): T {
  return structuredClone(fixture(name).payload) as T;
}
