// Perfiles y capacidades con falla cerrada (design.md §5.1–§5.2, NIT 4, DEC-032, PROD-009).
// `resolveProfile` es PURA: no lee window ni import.meta. main.tsx la llama una vez antes de
// montar y, si falla, muestra ConfigErrorPage sin hacer ninguna llamada a la API.

export type Profile = 'local' | 'demo' | 'escala';
export type AuthMode = 'none' | 'cognito';

export const SYNTHETIC_CLASSIFICATION = 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON';
export const DEFAULT_CACHE_TTL_HOURS = 12;
export const DEFAULT_REDIRECT_PATH = '/auth/callback';
export const API_PATH_SUFFIX = '/api/v1';

export interface RawEnv {
  readonly VITE_PROFILE?: string;
  readonly VITE_USE_MOCKS?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AUTH_MODE?: string;
  readonly VITE_COGNITO_AUTHORITY?: string;
  readonly VITE_COGNITO_DOMAIN?: string;
  readonly VITE_COGNITO_CLIENT_ID?: string;
  readonly VITE_COGNITO_SCOPES?: string;
  readonly VITE_COGNITO_REDIRECT_PATH?: string;
  readonly VITE_DATA_CLASSIFICATION?: string;
  readonly VITE_DEMO_CACHE_TTL_HOURS?: string;
  /** Operación PROPUESTA "Agregar información" (fuera de C3, DEC-039): '' | 'true' | 'false'. */
  readonly VITE_PROPOSAL_ADD_INFO?: string;
}

export interface Capabilities {
  readonly mocks: boolean;
  readonly authMode: AuthMode;
  /** IndexedDB Demo (caché + cola). Solo local/demo con clasificación sintética. */
  readonly persistence: boolean;
  readonly queue: boolean;
  /** SUP-038: Familia nueva no existe en `escala`. */
  readonly newFamily: boolean;
  /**
   * DEC-038: "nombre de trato" que la tía escribe y guarda SOLO en este equipo. Requiere
   * la persistencia Demo (local/demo sintético); oculto en `escala`.
   */
  readonly localNames: boolean;
  /**
   * DEC-039: botón "Agregar información" (operación propuesta, aún no está en C3). Activo por
   * defecto solo con mocks; con API real solo si VITE_PROPOSAL_ADD_INFO=true. Nunca en `escala`.
   */
  readonly addInfo: boolean;
  readonly syntheticBanner: boolean;
  readonly cacheTtlHours: number;
}

export interface CognitoConfig {
  readonly authority: string;
  readonly domain: string;
  readonly clientId: string;
  readonly scopes: string;
  readonly redirectPath: string;
}

/** Tipo de API resuelta: mocks en proceso, loopback, relativa `/api/v1` (proxy dev) o cloud. */
export type ApiKind = 'mock' | 'loopback' | 'relative' | 'cloud';

export interface ResolvedConfig {
  readonly profile: Profile;
  readonly capabilities: Capabilities;
  /** Base absoluta terminada en /api/v1, o `/api/v1` relativa (mocks/proxy local). */
  readonly apiBaseUrl: string;
  readonly apiKind: ApiKind;
  readonly cognito: CognitoConfig | null;
  /** Avisos no fatales (solo para log de desarrollo; nunca contienen valores). */
  readonly warnings: readonly ConfigWarning[];
}

export type ConfigIssue =
  | 'profile_unknown'
  | 'mocks_invalid'
  | 'mocks_forbidden_in_escala'
  | 'api_missing'
  | 'api_invalid'
  | 'api_relative_outside_local'
  | 'auth_mode_unknown'
  | 'auth_none_not_allowed'
  | 'cognito_authority_invalid'
  | 'cognito_domain_invalid'
  | 'cognito_client_id_invalid'
  | 'cognito_scopes_invalid'
  | 'cognito_redirect_path_invalid'
  | 'cognito_insecure_context'
  | 'insecure_context';

export type ConfigWarning = 'cache_ttl_invalid' | 'persistence_disabled_not_synthetic' | 'add_info_flag_invalid';

export type ProfileResult =
  | { readonly ok: true; readonly config: ResolvedConfig }
  | { readonly ok: false; readonly issues: readonly ConfigIssue[] };

export interface ResolveOptions {
  /** `window.isSecureContext` (inyectado para que la función siga siendo pura). */
  readonly isSecureContext: boolean;
}

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
const COGNITO_AUTHORITY_RE = /^https:\/\/cognito-idp\.[a-z0-9-]+\.amazonaws\.com\/[a-z0-9-]+_[A-Za-z0-9]+$/;
const CLIENT_ID_RE = /^[a-z0-9]{1,128}$/;
const SCOPE_RE = /^[A-Za-z0-9_./:-]{1,128}$/;
const REDIRECT_PATH_RE = /^\/(?!\/)[A-Za-z0-9/_-]*$/;

const blank = (value: string | undefined): boolean => value === undefined || value.trim() === '';

type ApiCheck = { ok: true; kind: Exclude<ApiKind, 'mock'>; base: string } | { ok: false; issue: ConfigIssue };

function checkApiUrl(raw: string | undefined, profile: Profile): ApiCheck {
  if (blank(raw)) return { ok: false, issue: 'api_missing' };
  const value = (raw as string).trim();
  if (value.startsWith('/')) {
    if (value !== API_PATH_SUFFIX && value !== `${API_PATH_SUFFIX}/`) return { ok: false, issue: 'api_invalid' };
    if (profile !== 'local') return { ok: false, issue: 'api_relative_outside_local' };
    return { ok: true, kind: 'relative', base: API_PATH_SUFFIX };
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return { ok: false, issue: 'api_invalid' };
  }
  if (url.username !== '' || url.password !== '' || url.search !== '' || url.hash !== '') {
    return { ok: false, issue: 'api_invalid' };
  }
  if (value.includes('?') || value.includes('#')) return { ok: false, issue: 'api_invalid' };
  const pathname = url.pathname.replace(/\/$/, '');
  if (!pathname.endsWith(API_PATH_SUFFIX)) return { ok: false, issue: 'api_invalid' };
  const loopback = LOOPBACK_HOSTS.has(url.hostname);
  if (url.protocol === 'https:') {
    return { ok: true, kind: loopback ? 'loopback' : 'cloud', base: `${url.origin}${pathname}` };
  }
  if (url.protocol === 'http:' && loopback) return { ok: true, kind: 'loopback', base: `${url.origin}${pathname}` };
  return { ok: false, issue: 'api_invalid' };
}

function checkHttpsOrigin(raw: string | undefined, allowPath: boolean): string | null {
  if (blank(raw)) return null;
  try {
    const url = new URL((raw as string).trim());
    if (url.protocol !== 'https:' || url.username !== '' || url.password !== '' || url.search !== '' || url.hash !== '') {
      return null;
    }
    if (!allowPath && url.pathname !== '/') return null;
    return allowPath ? `${url.origin}${url.pathname.replace(/\/$/, '')}` : url.origin;
  } catch {
    return null;
  }
}

function resolveCognito(env: RawEnv, issues: ConfigIssue[]): CognitoConfig | null {
  const authorityRaw = env.VITE_COGNITO_AUTHORITY?.trim() ?? '';
  const authority = COGNITO_AUTHORITY_RE.test(authorityRaw) ? checkHttpsOrigin(authorityRaw, true) : null;
  if (authority === null) issues.push('cognito_authority_invalid');
  const domain = checkHttpsOrigin(env.VITE_COGNITO_DOMAIN, false);
  if (domain === null) issues.push('cognito_domain_invalid');
  const clientId = env.VITE_COGNITO_CLIENT_ID?.trim() ?? '';
  if (!CLIENT_ID_RE.test(clientId)) issues.push('cognito_client_id_invalid');
  const scopeList = (env.VITE_COGNITO_SCOPES ?? '').trim().split(/\s+/).filter((s) => s !== '');
  if (scopeList.length === 0 || !scopeList.every((s) => SCOPE_RE.test(s))) issues.push('cognito_scopes_invalid');
  const redirectPath = blank(env.VITE_COGNITO_REDIRECT_PATH)
    ? DEFAULT_REDIRECT_PATH
    : (env.VITE_COGNITO_REDIRECT_PATH as string).trim();
  if (!REDIRECT_PATH_RE.test(redirectPath)) issues.push('cognito_redirect_path_invalid');
  if (authority === null || domain === null) return null;
  return { authority, domain, clientId, scopes: scopeList.join(' '), redirectPath };
}

export function resolveProfile(env: RawEnv, options: ResolveOptions): ProfileResult {
  const issues: ConfigIssue[] = [];
  const warnings: ConfigWarning[] = [];

  const profileRaw = blank(env.VITE_PROFILE) ? 'local' : (env.VITE_PROFILE as string).trim();
  if (profileRaw !== 'local' && profileRaw !== 'demo' && profileRaw !== 'escala') {
    return { ok: false, issues: ['profile_unknown'] };
  }
  const profile: Profile = profileRaw;

  const mocksRaw = blank(env.VITE_USE_MOCKS) ? 'false' : (env.VITE_USE_MOCKS as string).trim();
  if (mocksRaw !== 'true' && mocksRaw !== 'false') issues.push('mocks_invalid');
  const mocks = mocksRaw === 'true';
  if (mocks && profile === 'escala') issues.push('mocks_forbidden_in_escala');

  const authRaw = blank(env.VITE_AUTH_MODE) ? 'none' : (env.VITE_AUTH_MODE as string).trim();
  if (authRaw !== 'none' && authRaw !== 'cognito') issues.push('auth_mode_unknown');
  const authMode: AuthMode = authRaw === 'cognito' ? 'cognito' : 'none';

  // API: con mocks se usa la ruta relativa en proceso; sin mocks se exige URL válida.
  let apiKind: ApiKind = 'mock';
  let apiBaseUrl = API_PATH_SUFFIX;
  if (!mocks) {
    const api = checkApiUrl(env.VITE_API_BASE_URL, profile);
    if (api.ok) {
      apiKind = api.kind;
      apiBaseUrl = api.base;
    } else {
      issues.push(api.issue);
    }
  }

  // NIT 4 — `none` solo con mocks, o con API loopback/relativa en `local`.
  // demo + loopback + none es fatal (el fallback loopback usa `local`).
  if (authRaw === 'none') {
    const loopbackLocal = profile === 'local' && (apiKind === 'loopback' || apiKind === 'relative');
    const apiResolved = !issues.some((i) => i.startsWith('api_'));
    if (!mocks && apiResolved && !loopbackLocal) issues.push('auth_none_not_allowed');
  }

  let cognito: CognitoConfig | null = null;
  if (authMode === 'cognito') {
    cognito = resolveCognito(env, issues);
    // PKCE S256 usa crypto.subtle, que solo existe en contexto seguro.
    if (!options.isSecureContext) issues.push('cognito_insecure_context');
  }

  // Fuera de contexto seguro no hay SW ni transporte cifrado garantizado: solo `local`.
  if (!options.isSecureContext && profile !== 'local') issues.push('insecure_context');

  const synthetic = env.VITE_DATA_CLASSIFICATION === SYNTHETIC_CLASSIFICATION;
  const persistence = profile !== 'escala' && synthetic;
  if (profile !== 'escala' && !synthetic) warnings.push('persistence_disabled_not_synthetic');

  let cacheTtlHours = DEFAULT_CACHE_TTL_HOURS;
  if (!blank(env.VITE_DEMO_CACHE_TTL_HOURS)) {
    const raw = (env.VITE_DEMO_CACHE_TTL_HOURS as string).trim();
    const parsed = /^\d{1,2}$/.test(raw) ? Number(raw) : Number.NaN;
    if (Number.isInteger(parsed) && parsed >= 1 && parsed <= 72) cacheTtlHours = parsed;
    else warnings.push('cache_ttl_invalid');
  }

  // DEC-039: '' → activo solo con mocks; 'true'/'false' explícitos; otro valor → oculto (falla cerrada).
  const addInfoRaw = blank(env.VITE_PROPOSAL_ADD_INFO) ? '' : (env.VITE_PROPOSAL_ADD_INFO as string).trim();
  let addInfoFlag = mocks;
  if (addInfoRaw === 'true') addInfoFlag = true;
  else if (addInfoRaw === 'false') addInfoFlag = false;
  else if (addInfoRaw !== '') {
    addInfoFlag = false;
    warnings.push('add_info_flag_invalid');
  }

  if (issues.length > 0) return { ok: false, issues: [...new Set(issues)] };

  return {
    ok: true,
    config: {
      profile,
      capabilities: {
        mocks,
        authMode,
        persistence,
        queue: persistence,
        newFamily: profile !== 'escala',
        localNames: persistence,
        addInfo: profile !== 'escala' && addInfoFlag,
        syntheticBanner: profile !== 'escala',
        cacheTtlHours,
      },
      apiBaseUrl,
      apiKind,
      cognito,
      warnings,
    },
  };
}

/** Lee las variables VITE_* (reemplazo estático de Vite: cada clave se nombra literal). */
export function readViteEnv(): RawEnv {
  return {
    VITE_PROFILE: import.meta.env.VITE_PROFILE,
    VITE_USE_MOCKS: import.meta.env.VITE_USE_MOCKS,
    VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
    VITE_AUTH_MODE: import.meta.env.VITE_AUTH_MODE,
    VITE_COGNITO_AUTHORITY: import.meta.env.VITE_COGNITO_AUTHORITY,
    VITE_COGNITO_DOMAIN: import.meta.env.VITE_COGNITO_DOMAIN,
    VITE_COGNITO_CLIENT_ID: import.meta.env.VITE_COGNITO_CLIENT_ID,
    VITE_COGNITO_SCOPES: import.meta.env.VITE_COGNITO_SCOPES,
    VITE_COGNITO_REDIRECT_PATH: import.meta.env.VITE_COGNITO_REDIRECT_PATH,
    VITE_DATA_CLASSIFICATION: import.meta.env.VITE_DATA_CLASSIFICATION,
    VITE_DEMO_CACHE_TTL_HOURS: import.meta.env.VITE_DEMO_CACHE_TTL_HOURS,
    VITE_PROPOSAL_ADD_INFO: import.meta.env.VITE_PROPOSAL_ADD_INFO,
  };
}

// --- Configuración activa del proceso (se fija una sola vez en main.tsx) ---

let active: ResolvedConfig | null = null;

export function configureRuntime(config: ResolvedConfig): void {
  active = config;
}

/** Configuración validada. Lanza si main.tsx aún no la fijó (falla cerrada). */
export function runtimeConfig(): ResolvedConfig {
  if (active === null) throw new Error('runtime_config_missing');
  return active;
}

export function resetRuntimeForTests(): void {
  active = null;
}
