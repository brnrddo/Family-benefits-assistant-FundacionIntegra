// Plugin Vite propio (design.md §7.2, NIT 6): lee `content/i18n/es.json` y `content/manifest.yaml`
// al compilar (si existen), los valida en Node y expone `virtual:brujula-content`.
// No hay parseo YAML ni validación de C4 en el navegador. Los issues llevan solo clave y motivo.
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import type { Plugin } from 'vite';
import { parse as parseYaml } from 'yaml';

export type Profile = 'local' | 'demo' | 'escala';
export type CopyStatus = 'CANONICAL' | 'MISSING' | 'INVALID';
export type CopySource = 'CANONICAL' | 'MOCK_LOCAL' | 'MIXED';
export type C4Status = 'VALID' | 'MISSING' | 'INVALID';

export interface CatalogEntryLike {
  readonly placeholders: readonly string[];
  readonly optional?: boolean;
}
export type CatalogLike = Readonly<Record<string, CatalogEntryLike>>;

export interface ContentIssue {
  readonly key: string | null;
  readonly reason: string;
}

export interface ResolveContentInput {
  readonly contentDir: string;
  readonly schemaC4Path: string;
  readonly c3Meta: { readonly disclaimer: string };
  readonly catalog: CatalogLike;
  readonly mockValues: Readonly<Record<string, string>>;
  readonly profile: Profile;
  readonly allowMock: boolean;
}

export interface ResolvedContent {
  readonly strict: boolean;
  readonly copy: {
    readonly status: CopyStatus;
    readonly source: CopySource;
    readonly values: Readonly<Record<string, string>>;
    readonly issues: readonly ContentIssue[];
    readonly warnings: readonly ContentIssue[];
  };
  readonly c4: {
    readonly status: C4Status;
    readonly contentVersion: string | null;
    readonly contentBundleHash: string | null;
    readonly accessibility: unknown;
    readonly kpi: { readonly max_query_days: number; readonly min_cell_size: number } | null;
    readonly issues: readonly ContentIssue[];
  };
}

export const CANONICAL_I18N_PATH = 'content/i18n/es.json';
const KEY_RE = /^[a-z0-9_.-]+$/;
const PLACEHOLDER_RE = /\{([^{}]*)\}/g;
const MAX_VALUE_LENGTH = 600;

/** Error de política de copy: hace fallar el build. El mensaje no incluye valores. */
export class ContentPolicyError extends Error {
  readonly issues: readonly ContentIssue[];
  constructor(message: string, issues: readonly ContentIssue[] = []) {
    super(message);
    this.name = 'ContentPolicyError';
    this.issues = issues;
  }
}

const normalizeLf = (text: string): string => text.replace(/\r\n/g, '\n');
const sha256 = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');
const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

function placeholdersOf(value: string): string[] {
  return [...value.matchAll(PLACEHOLDER_RE)].map((m) => m[1] ?? '');
}

function sameSet(a: readonly string[], b: readonly string[]): boolean {
  const sa = new Set(a);
  const sb = new Set(b);
  return sa.size === sb.size && [...sa].every((x) => sb.has(x));
}

interface CopyValidation {
  status: CopyStatus;
  validValues: Record<string, string>;
  invalidKeys: Set<string>;
  issues: ContentIssue[];
  warnings: ContentIssue[];
}

function validateCopy(file: string, catalog: CatalogLike, disclaimer: string): CopyValidation {
  const result: CopyValidation = { status: 'MISSING', validValues: {}, invalidKeys: new Set(), issues: [], warnings: [] };
  if (!existsSync(file)) return result;
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(file, 'utf8'));
  } catch {
    result.status = 'INVALID';
    result.issues.push({ key: null, reason: 'json_parse' });
    return result;
  }
  if (!isPlainObject(parsed)) {
    result.status = 'INVALID';
    result.issues.push({ key: null, reason: 'not_flat_object' });
    return result;
  }
  for (const key of Object.keys(parsed)) {
    if (!KEY_RE.test(key)) result.issues.push({ key: null, reason: 'key_pattern' });
    else if (!(key in catalog)) result.warnings.push({ key, reason: 'extra_key_ignored' });
  }
  for (const [key, entry] of Object.entries(catalog)) {
    const value = parsed[key];
    if (value === undefined) {
      if (entry.optional !== true) {
        result.issues.push({ key, reason: 'missing' });
        result.invalidKeys.add(key);
      }
      continue;
    }
    let reason: string | null = null;
    if (typeof value !== 'string') reason = 'not_string';
    else if (value.length > MAX_VALUE_LENGTH) reason = 'too_long';
    else if (/<[A-Za-z]/.test(value)) reason = 'markup';
    else if (/javascript:/i.test(value)) reason = 'javascript_url';
    else if (!sameSet(placeholdersOf(value), entry.placeholders)) reason = 'placeholders';
    else if (key === 'notice.referential' && value !== disclaimer) reason = 'notice_mismatch';
    if (reason !== null) {
      result.issues.push({ key, reason });
      result.invalidKeys.add(key);
    } else {
      result.validValues[key] = value as string;
    }
  }
  result.status = result.issues.length === 0 ? 'CANONICAL' : 'INVALID';
  return result;
}

function validateC4(contentDir: string, schemaC4Path: string): ResolvedContent['c4'] {
  const missing = { status: 'MISSING' as const, contentVersion: null, contentBundleHash: null, accessibility: null, kpi: null };
  const manifestPath = path.join(contentDir, 'manifest.yaml');
  if (!existsSync(manifestPath)) return { ...missing, issues: [] };
  const invalid = (reason: string, key: string | null = null): ResolvedContent['c4'] => ({
    status: 'INVALID',
    contentVersion: null,
    contentBundleHash: null,
    accessibility: null,
    kpi: null,
    issues: [{ key, reason }],
  });
  let manifest: unknown;
  try {
    manifest = parseYaml(readFileSync(manifestPath, 'utf8'));
  } catch {
    return invalid('yaml_parse');
  }
  let validate: ReturnType<Ajv2020['compile']>;
  try {
    // NIT 6: mismas opciones que §6.1; `strict: true` a secas no compila C4 (strictTypes).
    const ajv = new Ajv2020({ strict: true, strictTypes: false, allowUnionTypes: true });
    validate = ajv.compile(JSON.parse(readFileSync(schemaC4Path, 'utf8')) as object);
  } catch {
    return invalid('schema_compile');
  }
  if (!validate(manifest)) {
    const first = validate.errors?.[0];
    return invalid('schema', first ? `${first.instancePath || '/'}:${first.keyword}` : null);
  }
  const m = manifest as {
    content_version: string;
    content_bundle_hash: string;
    canonical_i18n: string;
    files: { path: string; sha256: string; kind: string }[];
    kpi: { max_query_days: number; min_cell_size: number };
    accessibility: unknown;
  };
  if (m.canonical_i18n !== CANONICAL_I18N_PATH) return invalid('canonical_i18n');
  const entry = m.files.find((f) => f.kind === 'I18N' && f.path === CANONICAL_I18N_PATH);
  if (entry === undefined) return invalid('i18n_entry_missing');
  const i18nFile = path.join(contentDir, 'i18n', 'es.json');
  if (!existsSync(i18nFile)) return invalid('i18n_file_missing');
  if (sha256(normalizeLf(readFileSync(i18nFile, 'utf8'))) !== entry.sha256) return invalid('i18n_hash_mismatch');
  return {
    status: 'VALID',
    contentVersion: m.content_version,
    contentBundleHash: m.content_bundle_hash,
    accessibility: m.accessibility,
    kpi: { max_query_days: m.kpi.max_query_days, min_cell_size: m.kpi.min_cell_size },
    issues: [],
  };
}

/**
 * Función pura de resolución (§7.2). Lanza ContentPolicyError si la política lo exige:
 * mock en `escala`, o copy no canónico con política estricta.
 */
export function resolveContent(input: ResolveContentInput): ResolvedContent {
  const { contentDir, schemaC4Path, c3Meta, catalog, mockValues, profile, allowMock } = input;
  if (allowMock && profile === 'escala') {
    throw new ContentPolicyError('brujula-content: mock copy prohibido en escala');
  }
  const strict = profile === 'escala' || (profile === 'demo' && !allowMock);
  const copy = validateCopy(path.join(contentDir, 'i18n', 'es.json'), catalog, c3Meta.disclaimer);
  if (strict && copy.status !== 'CANONICAL') {
    const summary = copy.issues.map((i) => `${i.key ?? '*'}:${i.reason}`).join(', ');
    throw new ContentPolicyError(
      `brujula-content: copy canónico requerido en perfil ${profile} (estado ${copy.status})${summary ? `: ${summary}` : ''}`,
      copy.issues,
    );
  }
  let values: Record<string, string>;
  let source: CopySource;
  if (copy.status === 'CANONICAL') {
    values = { ...copy.validValues };
    source = 'CANONICAL';
  } else {
    values = {};
    let usedCanonical = 0;
    for (const key of Object.keys(catalog)) {
      const canonical = copy.validValues[key];
      if (canonical !== undefined) {
        values[key] = canonical;
        usedCanonical += 1;
      } else if (mockValues[key] !== undefined) {
        values[key] = mockValues[key];
      }
    }
    source = usedCanonical === 0 ? 'MOCK_LOCAL' : 'MIXED';
  }
  return {
    strict,
    copy: { status: copy.status, source, values, issues: copy.issues, warnings: copy.warnings },
    c4: validateC4(contentDir, schemaC4Path),
  };
}

const VIRTUAL_ID = 'virtual:brujula-content';
const RESOLVED_ID = `\0${VIRTUAL_ID}`;

export interface BrujulaContentOptions extends ResolveContentInput {
  /** Build con mocks (solo se informa en build-info.json para check-budget). */
  readonly mocks: boolean;
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function virtualModuleSource(resolved: ResolvedContent): string {
  const kpi = resolved.c4.status === 'VALID' ? (resolved.c4.kpi?.max_query_days ?? null) : null;
  return [
    `export const copyValues = Object.freeze(${JSON.stringify(resolved.copy.values)});`,
    `export const copySource = ${JSON.stringify(resolved.copy.source)};`,
    `export const c4Status = ${JSON.stringify(resolved.c4.status)};`,
    `export const contentVersion = ${JSON.stringify(resolved.c4.contentVersion)};`,
    `export const accessibility = ${JSON.stringify(resolved.c4.status === 'VALID' ? resolved.c4.accessibility : null)};`,
    `export const kpiMaxQueryDays = ${JSON.stringify(kpi)};`,
    '',
  ].join('\n');
}

export function brujulaContent(options: BrujulaContentOptions): Plugin {
  let resolved: ResolvedContent | null = null;
  const resolve = (): ResolvedContent => {
    resolved ??= resolveContent(options);
    return resolved;
  };
  const watched = [
    path.join(options.contentDir, 'i18n', 'es.json'),
    path.join(options.contentDir, 'manifest.yaml'),
  ];
  return {
    name: 'brujula-content',
    enforce: 'pre',
    buildStart() {
      resolved = null;
      const result = resolve();
      for (const file of watched) if (existsSync(file)) this.addWatchFile(file);
      if (result.copy.source !== 'CANONICAL') {
        this.warn(`copy ${result.copy.source} (estado ${result.copy.status}); insignia de copy provisional visible`);
      }
      if (result.c4.status !== 'VALID') {
        this.warn(`C4 ${result.c4.status}${result.c4.issues[0] ? ` (${result.c4.issues[0].reason})` : ''}; Polly/Translate ocultos`);
      }
      for (const warning of result.copy.warnings.slice(0, 5)) this.warn(`es.json: ${warning.key}:${warning.reason}`);
    },
    resolveId(id) {
      return id === VIRTUAL_ID ? RESOLVED_ID : null;
    },
    load(id) {
      return id === RESOLVED_ID ? virtualModuleSource(resolve()) : null;
    },
    handleHotUpdate({ file, server }) {
      if (!watched.some((w) => path.resolve(w) === path.resolve(file))) return;
      resolved = null;
      const mod = server.moduleGraph.getModuleById(RESOLVED_ID);
      if (mod) server.moduleGraph.invalidateModule(mod);
      server.ws.send({ type: 'full-reload' });
      return [];
    },
    transformIndexHtml(html) {
      const name = resolve().copy.values['app.name'];
      return name === undefined ? html : html.replace(/<title>[^<]*<\/title>/, `<title>${escapeHtml(name)}</title>`);
    },
    generateBundle() {
      const result = resolve();
      this.emitFile({
        type: 'asset',
        fileName: 'build-info.json',
        source: `${JSON.stringify({ profile: options.profile, mocks: options.mocks, copySource: result.copy.source, c4Status: result.c4.status })}\n`,
      });
    },
  };
}
