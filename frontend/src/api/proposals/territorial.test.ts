// Operación PROPUESTA "alcance territorial" (DEC-072, fuera de C3 v1.0.2): schema local cerrado con
// validador al día y fixture sintético del mock-servidor válido.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import fixture from '../../mocks/proposals/getCatalogoAlcance.json';
import meta from './generated/proposals.meta.json';
import { validateCatalogScopeEnvelopeV1 } from './generated/validators.gen.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_FILE = 'CatalogScopeEnvelopeV1.schema.json';
const schemaText = readFileSync(path.join(HERE, SCHEMA_FILE), 'utf8').replace(/\r\n/g, '\n');

describe('propuesta getCatalogoAlcance', () => {
  it('validador generado al día; fixture rotulado válido y con propiedad extra inválido', () => {
    const hash = createHash('sha256').update(schemaText, 'utf8').digest('hex');
    expect((meta.files as Record<string, string>)[SCHEMA_FILE], 'schema cambió: ejecute npm run gen:proposals').toBe(hash);
    expect(fixture.data_classification).toBe('SYNTHETIC_DEMO_NOT_A_REAL_PERSON');
    expect(validateCatalogScopeEnvelopeV1(fixture.payload)).toBe(true);
    expect(fixture.payload.items.filter((item) => item.demo).map((item) => [item.benefit_id, item.scope])).toEqual([['BEN-DEMO-LOCAL-01', 'LOCAL']]);
    const extra = structuredClone(fixture.payload);
    (extra.items[0] as Record<string, unknown>).commune_id = 'COM-001';
    expect(validateCatalogScopeEnvelopeV1(extra)).toBe(false);
  });
});
