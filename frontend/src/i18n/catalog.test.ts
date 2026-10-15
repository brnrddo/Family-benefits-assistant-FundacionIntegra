import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import meta from '../api/generated/c3.meta.json';
import { CATALOG_META, COPY_CATALOG, COPY_KEYS, isOptionalKey } from './catalog';
import { buildCatalogExport } from './catalogExport';
import { MOCK_COPY } from './es.mock';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const placeholdersOf = (value: string) => [...value.matchAll(/\{([^{}]*)\}/g)].map((m) => m[1]).sort();

describe('i18n — catálogo v1.2.0 (§7.1)', () => {
  it('tiene 407 claves con el patrón de C4 y versión 1.2.0', () => {
    expect(CATALOG_META.catalog_version).toBe('1.2.0');
    expect(COPY_KEYS).toHaveLength(407);
    for (const key of COPY_KEYS) expect(key).toMatch(/^[a-z0-9_.-]+$/);
  });


  it('incluye las tres claves nuevas de 1.1.0', () => {
    expect(COPY_CATALOG['new_family.date_future'].placeholders).toEqual([]);
    expect(COPY_CATALOG['kpi.range_invalid'].placeholders).toEqual([]);
    expect(COPY_CATALOG['kpi.range_too_long'].placeholders).toEqual(['max_days']);
    expect(COPY_CATALOG['kpi.range_too_long'].tipo).toEqual({ max_days: 'integer' });
  });

  it('solo benefit.*.name son opcionales', () => {
    const optional = COPY_KEYS.filter(isOptionalKey);
    expect(optional).toHaveLength(20);
    expect(optional.every((k) => /^benefit\.ben-\d{3}\.name$/.test(k))).toBe(true);
  });

  it('frontend/i18n-catalog.json es igual al export (npm run export:i18n-catalog)', () => {
    const versioned = JSON.parse(readFileSync(path.resolve(HERE, '../../i18n-catalog.json'), 'utf8')) as unknown;
    expect(versioned).toEqual(JSON.parse(JSON.stringify(buildCatalogExport())));
  });
});

describe('i18n — copy MOCK_LOCAL (SUP-030)', () => {
  it('cubre las 407 claves, sin extras, con los placeholders exactos', () => {
    expect(Object.keys(MOCK_COPY).sort()).toEqual([...COPY_KEYS].sort());
    for (const key of COPY_KEYS) {
      const value: string = MOCK_COPY[key];
      expect(placeholdersOf(value), key).toEqual([...COPY_CATALOG[key].placeholders].sort());
      expect(value.length).toBeLessThanOrEqual(600);
      expect(value).not.toMatch(/<[A-Za-z]/);
      expect(value).not.toMatch(/javascript:/i);
    }
  });

  it('notice.referential es idéntico al disclaimer const de C3', () => {
    expect(MOCK_COPY['notice.referential']).toBe(meta.disclaimer);
  });

  it('empieza con la cabecera MOCK_LOCAL', () => {
    const source = readFileSync(path.join(HERE, 'es.mock.ts'), 'utf8');
    expect(source.startsWith('// MOCK_LOCAL — copy provisional NO canónico (SUP-030)')).toBe(true);
  });
});
