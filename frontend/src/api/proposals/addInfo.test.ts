// Operación PROPUESTA "Agregar información" (DEC-039, PREG-039): schema local cerrado con validador
// al día y subconjunto exacto de PreevaluationRequest (C3); fixture sintético coherente con el mock.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { parse as parseYaml } from 'yaml';
import { reevaluateWithDeclared } from '../../mocks/handlers';
import fixture from '../../mocks/proposals/addFamiliaAntecedentes.FAM-SIM-E3-00002.json';
import { fichaPreguntar } from '../../test/fixtures';
import { validateFamiliaDetailEnvelope } from '../generated/validators.gen.js';
import meta from './generated/proposals.meta.json';
import { validateAddFamilyInfoRequestV1 } from './generated/validators.gen.js';
import type { AddFamilyInfoRequestV1 } from './types';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_FILE = 'AddFamilyInfoRequestV1.schema.json';
const schemaText = readFileSync(path.join(HERE, SCHEMA_FILE), 'utf8').replace(/\r\n/g, '\n');

describe('propuesta addFamiliaAntecedentes', () => {
  it('schema cerrado = campos cerrados de PreevaluationRequest; validador generado al día', () => {
    const hash = createHash('sha256').update(schemaText, 'utf8').digest('hex');
    expect((meta.files as Record<string, string>)[SCHEMA_FILE], 'schema cambió: ejecute npm run gen:proposals').toBe(hash);
    const schema = JSON.parse(schemaText) as { properties: Record<string, unknown>; additionalProperties: boolean };
    const c3Path = path.resolve(HERE, '../../../../.kiro/specs/_shared/contracts/C3-api.openapi.yaml');
    const c3 = parseYaml(readFileSync(c3Path, 'utf8')) as { components: { schemas: { PreevaluationRequest: { properties: Record<string, unknown> } } } };
    const closed = { ...c3.components.schemas.PreevaluationRequest.properties };
    for (const key of ['garden_id', 'commune_id', 'demo_notice_accepted']) delete closed[key];
    expect(schema.additionalProperties).toBe(false);
    expect(schema.properties).toEqual(closed);
    expect(validateAddFamilyInfoRequestV1(fixture.request)).toBe(true);
    expect(validateAddFamilyInfoRequestV1({ data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON', child_name: 'Ana' })).toBe(false);
  });

  it('fixture rotulado y válido; el mock-servidor re-evalúa exactamente a esa ficha', () => {
    expect(fixture.data_classification).toBe('SYNTHETIC_DEMO_NOT_A_REAL_PERSON');
    expect(validateFamiliaDetailEnvelope(fixture.payload)).toBe(true);
    expect(reevaluateWithDeclared(fichaPreguntar().data, fixture.request as AddFamilyInfoRequestV1)).toEqual(fixture.payload.data);
  });
});
