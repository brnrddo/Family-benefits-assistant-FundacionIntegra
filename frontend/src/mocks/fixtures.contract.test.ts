// Rotulado y validez contractual de cada fixture (design.md §8, §15; PRIVACIDAD_DEMO.md).
import { describe, expect, it } from 'vitest';
import { formats } from '../api/contract/runtime.js';
import meta from '../api/generated/c3.meta.json';
import * as validators from '../api/generated/validators.gen.js';
import { isSyntheticId } from '../domain/ids';
import { containsPii } from '../domain/piiGuard';
import { data_classification } from '../test/fixtures';
import { FIXTURES, SYNTHETIC_CLASSIFICATION } from './fixtureStore';
import * as variants from './variants';

type Validator = (data: unknown) => boolean;
const byName = validators as unknown as Record<string, Validator>;
const operations = meta.operations as Record<string, { expectedStatus: number; response: string }>;
const ERROR_STATUSES = [401, 403, 404, 409, 422, 429, 503];

function strings(value: unknown, out: string[] = []): string[] {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => strings(v, out));
  else if (value !== null && typeof value === 'object') Object.values(value).forEach((v) => strings(v, out));
  return out;
}

function idsByKey(value: unknown, keys: ReadonlySet<string>, out: unknown[] = []): unknown[] {
  if (Array.isArray(value)) value.forEach((v) => idsByKey(v, keys, out));
  else if (value !== null && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      if (keys.has(k)) out.push(v);
      idsByKey(v, keys, out);
    }
  }
  return out;
}

const entries = Object.entries(FIXTURES);

describe('fixtures sintéticos', () => {
  it('existen y test/fixtures.ts exporta el literal de clasificación', () => {
    expect(entries.length).toBeGreaterThanOrEqual(40);
    expect(data_classification).toBe('SYNTHETIC_DEMO_NOT_A_REAL_PERSON');
    expect(SYNTHETIC_CLASSIFICATION).toBe('SYNTHETIC_DEMO_NOT_A_REAL_PERSON');
  });

  it.each(entries)('%s: rotulado y válido para su operación y status', (_name, fixture) => {
    expect(fixture.data_classification).toBe('SYNTHETIC_DEMO_NOT_A_REAL_PERSON');
    expect(Object.keys(fixture).sort()).toEqual(['data_classification', 'operationId', 'payload', 'status']);
    if (fixture.operationId === '*') {
      expect(ERROR_STATUSES).toContain(fixture.status);
      expect(byName.validateErrorResponse?.(fixture.payload)).toBe(true);
      return;
    }
    const op = operations[fixture.operationId];
    expect(op, `operationId desconocido: ${fixture.operationId}`).toBeDefined();
    expect(fixture.status).toBe(op?.expectedStatus);
    const validate = byName[`validate${op?.response}`];
    expect(validate?.(fixture.payload), JSON.stringify((validate as unknown as { errors?: unknown })?.errors)).toBe(true);
  });

  it.each(entries)('%s: sin PII detectable y con IDs -SIM- de familia/jardín', (_name, fixture) => {
    // UUID y fechas ISO calzan con el patrón de RUT/teléfono del guard (falso positivo conocido): se excluyen.
    const free = strings(fixture.payload).filter((s) => !formats.uuid(s) && !formats['date-time'](s) && !formats.date(s));
    for (const text of free) expect(containsPii(text), text.slice(0, 40)).toBe(false);
    for (const id of idsByKey(fixture.payload, new Set(['family_id', 'garden_id']))) expect(isSyntheticId(id)).toBe(true);
    const snapshots = idsByKey(fixture.payload, new Set(['snapshot_id']));
    for (const id of snapshots) expect(String(id)).toMatch(/^SNAP-SIM-DEMO-\d{3}$/);
    for (const hash of idsByKey(fixture.payload, new Set(['eligibility_bundle_hash']))) expect(hash).toBe('a'.repeat(64));
    for (const hash of idsByKey(fixture.payload, new Set(['content_bundle_hash']))) expect(hash).toBe('b'.repeat(64));
    for (const url of idsByKey(fixture.payload, new Set(['url']))) expect(String(url)).toMatch(/^https:\/\/fuentes\.brujula-demo\.example\//);
  });

  it('cubre el mínimo de §8', () => {
    const names = new Set(Object.keys(FIXTURES));
    for (const required of [
      'listJardines',
      'listFamiliasByJardin.JAR-SIM-E3-00001.p1',
      'listFamiliasByJardin.JAR-SIM-E3-00001.p2',
      'getFamilia.FAM-SIM-E3-00001',
      'getFamilia.FAM-SIM-E3-00002',
      'getFamilia.FAM-SIM-E3-00003',
      'createGuion.bedrock',
      'createGuion.plantilla',
      'createMensaje.bedrock',
      'createMensaje.plantilla',
      'createMensaje.adversarial',
      'getKpi',
      'getKpi.suppressed',
      'getKpi.nulls',
      'askCatalogAssistant.catalog-info',
      'askCatalogAssistant.deterministic',
      'createPreevaluacion',
      'ingestSyntheticFlyer',
      ...ERROR_STATUSES.map((s) => `error.${s}`),
    ]) {
      expect(names.has(required), required).toBe(true);
    }
    for (const family of ['FAM-SIM-E3-00001', 'FAM-SIM-E3-00002', 'FAM-SIM-E3-00003']) {
      for (const orden of ['prioridad', 'urgencia', 'beneficio']) expect(names.has(`listOportunidades.${family}.${orden}`)).toBe(true);
    }
    const families = [
      ...(FIXTURES['listFamiliasByJardin.JAR-SIM-E3-00001.p1']?.payload as { items: { traffic_light: string; conversation_status: string }[] }).items,
      ...(FIXTURES['listFamiliasByJardin.JAR-SIM-E3-00001.p2']?.payload as { items: { traffic_light: string; conversation_status: string }[] }).items,
    ];
    expect(families).toHaveLength(8);
    expect(new Set(families.map((f) => f.traffic_light))).toEqual(new Set(['VERDE', 'AMARILLO', 'AZUL', 'SIN_OPORTUNIDADES']));
    expect(new Set(families.map((f) => f.conversation_status))).toEqual(new Set(['PENDIENTE', 'CONVERSADA']));
  });

  it('las conversaciones sembradas por el servidor llevan origin SIMULADO_DEMO', () => {
    const seeds = Object.entries(FIXTURES).filter(([name]) => name.startsWith('createConversacion.seed.'));
    expect(seeds.length).toBeGreaterThanOrEqual(2);
    for (const [, seed] of seeds) expect((seed.payload as { data: { origin: string } }).data.origin).toBe('SIMULADO_DEMO');
  });

  it('el mensaje adversarial es VÁLIDO para C3 (strings de §11.4 y largos máximos)', () => {
    const payload = FIXTURES['createMensaje.adversarial']?.payload as {
      content: { whatsapp_preview: string; printable_card: { title: string; sections: { heading: string; reason: string }[] } };
    };
    expect(byName.validateMessageGenerationEnvelope?.(payload)).toBe(true);
    const text = strings(payload).join('\n');
    for (const needle of ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', '"><svg onload=alert(1)>', 'javascript:alert(1)', 'style="position:fixed"', 'url(https://evil.example)', '</article><a href="https://evil.example">x', "{{constructor.constructor('alert(1)')()}}", '\u202e']) {
      expect(text).toContain(needle);
    }
    expect([...payload.content.whatsapp_preview]).toHaveLength(600);
    expect([...(payload.content.printable_card.sections[1]?.heading ?? '')]).toHaveLength(100);
    expect([...(payload.content.printable_card.sections[1]?.reason ?? '')]).toHaveLength(240);
  });

  it('las variantes derivadas por clonación son INVÁLIDAS para C3', () => {
    expect(byName.validateMessageGenerationEnvelope?.(variants.messageWithHttpCitation())).toBe(false);
    expect(byName.validateMessageGenerationEnvelope?.(variants.messageWithJavascriptCitation())).toBe(false);
    expect(byName.validateMessageGenerationEnvelope?.(variants.messageWithHtmlProperty())).toBe(false);
    expect(byName.validateMessageGenerationEnvelope?.(variants.messageWithFourSections())).toBe(false);
    expect(byName.validateMessageGenerationEnvelope?.(variants.messageWithWrongFormatVersion())).toBe(false);
    expect(byName.validateOpportunityListEnvelope?.(variants.opportunitiesWithSiAndNullLevel())).toBe(false);
    expect(byName.validateJardinListEnvelope?.(variants.jardinesWithExtraProperty())).toBe(false);
    expect(byName.validateFamiliaListEnvelope?.(variants.familiasWithInvalidEnum())).toBe(false);
    expect(byName.validateErrorResponse?.({ message: 'Too Many Requests' })).toBe(false);
  });
});
