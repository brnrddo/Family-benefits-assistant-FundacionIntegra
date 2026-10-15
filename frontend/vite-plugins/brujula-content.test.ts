// Plugin brujula-content (§7.2, NIT 6): cada estado se fuerza con directorios temporales.
// El contenido de prueba es copy MOCK escrito por Rol 3 (no el es.json de Rol 4).
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import meta from '../src/api/generated/c3.meta.json';
import { COPY_CATALOG } from '../src/i18n/catalog';
import { MOCK_COPY } from '../src/i18n/es.mock';
import { brujulaContent, ContentPolicyError, resolveContent, virtualModuleSource, type Profile } from './brujula-content';

const SCHEMA_C4 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../.kiro/specs/_shared/contracts/C4-contenido-manifest.schema.json');
const dirs: string[] = [];

function contentDir(): string {
  const dir = mkdtempSync(path.join(tmpdir(), 'brujula content '));
  dirs.push(dir);
  return dir;
}

afterEach(() => {
  for (const dir of dirs.splice(0)) rmSync(dir, { recursive: true, force: true });
});

function writeCopy(dir: string, values: Record<string, unknown> | string, crlf = false): string {
  mkdirSync(path.join(dir, 'i18n'), { recursive: true });
  let text = typeof values === 'string' ? values : JSON.stringify(values, null, 2);
  if (crlf) text = text.replace(/\n/g, '\r\n');
  writeFileSync(path.join(dir, 'i18n', 'es.json'), text, 'utf8');
  return text;
}

const sha = (text: string) => createHash('sha256').update(text.replace(/\r\n/g, '\n'), 'utf8').digest('hex');

function manifest(i18nHash: string, overrides: Record<string, unknown> = {}) {
  return {
    schema_version: '1.0.0',
    content_version: '1.2.0',
    content_bundle_hash: 'b'.repeat(64),
    canonical_i18n: 'content/i18n/es.json',
    files: [
      { path: 'content/pesos_priorizacion.yaml', sha256: 'c'.repeat(64), kind: 'WEIGHTS' },
      { path: 'content/preguntas.yaml', sha256: 'c'.repeat(64), kind: 'QUESTIONS' },
      { path: 'content/beneficios.yaml', sha256: 'c'.repeat(64), kind: 'BENEFITS' },
      { path: 'content/prompts/guion.md', sha256: 'c'.repeat(64), kind: 'PROMPT' },
      { path: 'content/accessibility.yaml', sha256: 'c'.repeat(64), kind: 'ACCESSIBILITY' },
      { path: 'content/i18n/es.json', sha256: i18nHash, kind: 'I18N' },
    ],
    ranking: {
      axis_weights: { u: 0.4, b: 0.35, v: 0.25 },
      urgency: {
        aggregation: 'MAX',
        use_window: false,
        default_score: 0.1,
        recent_emergency: { benefit_id: 'BEN-001', max_age_days: 30, score: 0.9 },
        newborn_expiry: { benefit_id: 'BEN-002', window_days: 90, calculation: 'LINEAR_ELAPSED_OVER_WINDOW' },
        therapy_document_expiry: { benefit_id: 'BEN-003', window_days: 180, calculation: 'LINEAR_ELAPSED_OVER_WINDOW' },
        limited_quota: { score: 0.7 },
        food_insecurity: { minimum_index: 2, score: 0.8 },
        precarious_housing: { housing_types: ['CAMP_OR_OCCUPATION'], score: 0.8 },
        application_windows: [{ maximum_days_remaining: 7, score: 0.9 }],
      },
      benefit_impact: {
        annualization_multipliers: { MENSUAL: 12, ANUAL: 1, UNICA: 1 },
        max_income_share_for_full_score: 0.5,
        default_monthly_household_income: 500000,
        garden_income_medians: [],
        service_equivalences: [],
      },
      vulnerability: {
        unknown_signals_excluded: true,
        component_weights: { rsh: 0.3, income: 0.2, health_coverage: 0.1, cse: 0.2, female_head_program: 0.1, possible_child_disability: 0.1 },
        rsh_scores: { band_40: 1, band_50: 0.8, band_60: 0.6, band_70: 0.4, band_80: 0.2, band_90: 0.1, band_100: 0, no_rsh: 0.5 },
        income_band_scores: { UNDER_110K: 1, '110K_250K': 0.6, '250K_400K': 0.3, OVER_400K: 0 },
        health_coverage_scores: { FONASA_A: 1, NO_COVERAGE: 1 },
        cse: { comparison: 'LTE', threshold: 10, score: 1 },
        female_head_program_score: 0.5,
        possible_child_disability_score: 0.5,
      },
      opportunity_score: {
        state_weights: {
          ELEGIBLE_SIN_ASIGNACION: 1,
          GESTION_RECHAZADA: 0.8,
          PENDIENTE_ANTECEDENTES: 0.7,
          INDETERMINADO: 0.6,
          GESTION_EN_CURSO: 0.3,
          SIN_CUPO: 0.2,
          ASIGNADO: 0.1,
        },
        action_bonus: 0.1,
        resolvable_question_limit: 3,
      },
      family_priority: {
        top_opportunity_count: 3,
        vulnerability_multiplier: 1,
        not_informed_bonus: 0.1,
        new_family_bonus: 0.1,
        new_family_max_age_days: 30,
      },
    },
    kpi: { min_cell_size: 5, max_query_days: 92 },
    accessibility: {
      canonical_spanish_label_key: 'a11y.canonical_spanish_label',
      polly: {
        enabled: false,
        evidence_state: 'NO_VERIFICADO',
        smoke_test_evidence_id: null,
        allowed_voices: [],
        max_output_characters: 1000,
        fallback_label_key: 'a11y.audio_unavailable',
      },
      translate: {
        enabled: false,
        evidence_state: 'NO_VERIFICADO',
        smoke_test_evidence_id: null,
        source_language: 'es',
        allowed_target_languages: [],
        max_output_characters: 1000,
        fallback_label_key: 'a11y.translation_unavailable',
      },
    },
    ...overrides,
  };
}

function writeManifest(dir: string, value: unknown | string) {
  writeFileSync(path.join(dir, 'manifest.yaml'), typeof value === 'string' ? value : stringify(value), 'utf8');
}

function resolve(dir: string, profile: Profile = 'local', allowMock = false, schemaC4Path = SCHEMA_C4) {
  return resolveContent({
    contentDir: dir,
    schemaC4Path,
    c3Meta: { disclaimer: meta.disclaimer },
    catalog: COPY_CATALOG,
    mockValues: MOCK_COPY,
    profile,
    allowMock,
  });
}

const canonicalCopy = (): Record<string, string> => ({ ...MOCK_COPY });

describe('brujula-content — copy', () => {
  it('MISSING en local → MOCK_LOCAL clave por clave (407)', () => {
    const result = resolve(contentDir());
    expect(result.strict).toBe(false);
    expect(result.copy).toMatchObject({ status: 'MISSING', source: 'MOCK_LOCAL' });
    expect(Object.keys(result.copy.values)).toHaveLength(407);
    expect(result.c4.status).toBe('MISSING');
  });

  it('CANONICAL con todas las claves; las extra se ignoran con aviso', () => {
    const dir = contentDir();
    writeCopy(dir, { ...canonicalCopy(), 'clave.extra': 'texto' });
    const result = resolve(dir, 'escala');
    expect(result.strict).toBe(true);
    expect(result.copy).toMatchObject({ status: 'CANONICAL', source: 'CANONICAL', issues: [] });
    expect(result.copy.warnings).toEqual([{ key: 'clave.extra', reason: 'extra_key_ignored' }]);
    expect(result.copy.values['clave.extra']).toBeUndefined();
  });

  it('CANONICAL sin las claves opcionales benefit.*.name', () => {
    const dir = contentDir();
    const values = canonicalCopy();
    for (const key of Object.keys(values)) if (key.startsWith('benefit.')) delete values[key];
    writeCopy(dir, values);
    const result = resolve(dir, 'demo');
    expect(result.copy.status).toBe('CANONICAL');
    expect(result.copy.values['benefit.ben-001.name']).toBeUndefined();
  });

  it.each([
    ['clave faltante', (v: Record<string, unknown>) => delete v['kpi.range_invalid'], 'kpi.range_invalid', 'missing'],
    ['placeholder distinto', (v: Record<string, unknown>) => (v['home.progress'] = '{informed} de {otro}'), 'home.progress', 'placeholders'],
    ['placeholder faltante', (v: Record<string, unknown>) => (v['kpi.range_too_long'] = 'Período muy largo'), 'kpi.range_too_long', 'placeholders'],
    ['markup', (v: Record<string, unknown>) => (v['app.name'] = '<b>Brújula</b>'), 'app.name', 'markup'],
    ['javascript:', (v: Record<string, unknown>) => (v['app.tagline'] = 'ver javascript:alert(1)'), 'app.tagline', 'javascript_url'],
    ['> 600 caracteres', (v: Record<string, unknown>) => (v['app.tagline'] = 'x'.repeat(601)), 'app.tagline', 'too_long'],
    ['no string', (v: Record<string, unknown>) => (v['app.tagline'] = 3), 'app.tagline', 'not_string'],
    ['aviso distinto del disclaimer de C3', (v: Record<string, unknown>) => (v['notice.referential'] = 'Orientación referencial.'), 'notice.referential', 'notice_mismatch'],
  ])('INVALID: %s → MIXED en local (mock solo en esa clave)', (_name, mutate, key, reason) => {
    const dir = contentDir();
    const values: Record<string, unknown> = canonicalCopy();
    mutate(values);
    writeCopy(dir, values);
    const result = resolve(dir);
    expect(result.copy.status).toBe('INVALID');
    expect(result.copy.source).toBe('MIXED');
    expect(result.copy.issues).toContainEqual({ key, reason });
    expect(result.copy.values[key]).toBe(MOCK_COPY[key as keyof typeof MOCK_COPY]);
    // Los issues solo llevan clave y motivo: nunca valores.
    expect(JSON.stringify(result.copy.issues)).not.toMatch(/Brújula|alert|xxxx|\{otro\}/);
  });

  it('INVALID estructural: JSON roto, arreglo, clave con patrón inválido', () => {
    const broken = contentDir();
    writeCopy(broken, '{ no es json');
    expect(resolve(broken).copy).toMatchObject({ status: 'INVALID', source: 'MOCK_LOCAL', issues: [{ key: null, reason: 'json_parse' }] });
    const array = contentDir();
    writeCopy(array, '["a"]');
    expect(resolve(array).copy.issues).toEqual([{ key: null, reason: 'not_flat_object' }]);
    const badKey = contentDir();
    writeCopy(badKey, { ...canonicalCopy(), 'Clave Mala': 'x' });
    expect(resolve(badKey).copy).toMatchObject({ status: 'INVALID', source: 'MIXED' });
  });
});

describe('brujula-content — política estricta', () => {
  it('allowMock + escala → lanza antes de resolver (aunque haya copy canónico)', () => {
    const dir = contentDir();
    writeCopy(dir, canonicalCopy());
    expect(() => resolve(dir, 'escala', true)).toThrow('brujula-content: mock copy prohibido en escala');
  });

  it.each(['demo', 'escala'] as const)('%s sin copy canónico → lanza con la lista de issues', (profile) => {
    expect(() => resolve(contentDir(), profile)).toThrow(ContentPolicyError);
    const dir = contentDir();
    const values = canonicalCopy() as Record<string, string>;
    delete values['new_family.date_future'];
    writeCopy(dir, values);
    expect(() => resolve(dir, profile)).toThrow(/copy canónico requerido.*new_family\.date_future:missing/);
  });

  it('demo + allowMock (ensayo) → MOCK_LOCAL sin lanzar', () => {
    const result = resolve(contentDir(), 'demo', true);
    expect(result.strict).toBe(false);
    expect(result.copy.source).toBe('MOCK_LOCAL');
  });
});

describe('brujula-content — C4', () => {
  it('VALID con hash I18N sobre LF aunque el archivo tenga CRLF', () => {
    const dir = contentDir();
    const text = writeCopy(dir, canonicalCopy(), true);
    writeManifest(dir, manifest(sha(text)));
    const result = resolve(dir, 'escala');
    expect(result.c4).toMatchObject({ status: 'VALID', contentVersion: '1.2.0', contentBundleHash: 'b'.repeat(64), kpi: { max_query_days: 92 } });
    expect(virtualModuleSource(result)).toContain('export const kpiMaxQueryDays = 92;');
  });

  it('INVALID: schema, hash distinto, entrada I18N con otro path, YAML roto, es.json ausente', () => {
    const schema = contentDir();
    writeCopy(schema, canonicalCopy());
    writeManifest(schema, { ...manifest('a'.repeat(64)), kpi: { min_cell_size: 5, max_query_days: 999 } });
    expect(resolve(schema).c4).toMatchObject({ status: 'INVALID', issues: [{ reason: 'schema' }] });

    const hash = contentDir();
    writeCopy(hash, canonicalCopy());
    writeManifest(hash, manifest('a'.repeat(64)));
    expect(resolve(hash).c4.issues).toEqual([{ key: null, reason: 'i18n_hash_mismatch' }]);

    const otherPath = contentDir();
    const text = writeCopy(otherPath, canonicalCopy());
    const m = manifest(sha(text));
    m.files[5] = { path: 'content/i18n/otro.json', sha256: sha(text), kind: 'I18N' };
    writeManifest(otherPath, m);
    expect(resolve(otherPath).c4.issues).toEqual([{ key: null, reason: 'i18n_entry_missing' }]);

    const yaml = contentDir();
    writeManifest(yaml, 'files: [\n  - : :');
    expect(resolve(yaml).c4.issues).toEqual([{ key: null, reason: 'yaml_parse' }]);

    const noCopy = contentDir();
    writeManifest(noCopy, manifest('a'.repeat(64)));
    expect(resolve(noCopy).c4.issues).toEqual([{ key: null, reason: 'i18n_file_missing' }]);
  });

  it('NIT 6: si el schema C4 no compila → INVALID schema_compile, sin romper el build', () => {
    const dir = contentDir();
    writeCopy(dir, canonicalCopy());
    writeManifest(dir, manifest('a'.repeat(64)));
    const badSchema = path.join(dir, 'schema-roto.json');
    writeFileSync(badSchema, JSON.stringify({ type: 'objeto-inexistente' }), 'utf8');
    const result = resolve(dir, 'escala', false, badSchema);
    expect(result.copy.status).toBe('CANONICAL');
    expect(result.c4).toMatchObject({ status: 'INVALID', issues: [{ key: null, reason: 'schema_compile' }] });
  });

  it('C4 no VALID nunca exporta accessibility ni kpiMaxQueryDays', () => {
    const source = virtualModuleSource(resolve(contentDir()));
    expect(source).toContain('export const accessibility = null;');
    expect(source).toContain('export const kpiMaxQueryDays = null;');
    expect(source).toContain('export const copySource = "MOCK_LOCAL";');
  });
});

describe('brujula-content — plugin Vite', () => {
  it('resuelve y carga el módulo virtual con datos serializables', () => {
    const plugin = brujulaContent({
      contentDir: contentDir(),
      schemaC4Path: SCHEMA_C4,
      c3Meta: { disclaimer: meta.disclaimer },
      catalog: COPY_CATALOG,
      mockValues: MOCK_COPY,
      profile: 'local',
      allowMock: false,
      mocks: true,
    });
    const resolveId = plugin.resolveId as (id: string) => string | null;
    const load = plugin.load as (id: string) => string | null;
    const id = resolveId('virtual:brujula-content');
    expect(id).toBe('\0virtual:brujula-content');
    expect(load(id as string)).toContain('export const copyValues = Object.freeze(');
    expect(resolveId('otro')).toBeNull();
  });
});
