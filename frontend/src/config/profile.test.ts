// Matriz de §5.2 y tabla de verdad del NIT 4. Valores de Cognito/API ficticios (dominios
// reservados .example / .invalid y un pool inventado): ningún endpoint real.
import { describe, expect, it } from 'vitest';
import { resolveProfile, type ConfigIssue, type RawEnv } from './profile';

const SECURE = { isSecureContext: true };
const INSECURE = { isSecureContext: false };
const SYNTHETIC = 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON';

const COGNITO: RawEnv = {
  VITE_AUTH_MODE: 'cognito',
  VITE_COGNITO_AUTHORITY: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_SIMPOOL01',
  VITE_COGNITO_DOMAIN: 'https://auth.brujula-demo.example',
  VITE_COGNITO_CLIENT_ID: 'simclientid0001',
  VITE_COGNITO_SCOPES: 'openid jardines:read familias:read',
};
const CLOUD_API = 'https://api.brujula-demo.example/api/v1';

function issuesOf(env: RawEnv, opts = SECURE): readonly ConfigIssue[] {
  const result = resolveProfile(env, opts);
  return result.ok ? [] : result.issues;
}

function okConfig(env: RawEnv, opts = SECURE) {
  const result = resolveProfile(env, opts);
  if (!result.ok) throw new Error(`esperaba OK y falló: ${result.issues.join(',')}`);
  return result.config;
}

describe('resolveProfile — tabla de verdad NIT 4', () => {
  it('local + mocks + none → OK', () => {
    const config = okConfig({ VITE_PROFILE: 'local', VITE_USE_MOCKS: 'true', VITE_AUTH_MODE: 'none' });
    expect(config.apiKind).toBe('mock');
    expect(config.capabilities).toMatchObject({ mocks: true, authMode: 'none', newFamily: true, syntheticBanner: true });
  });

  it('local + sin mocks + API loopback o relativa + none → OK', () => {
    expect(okConfig({ VITE_PROFILE: 'local', VITE_API_BASE_URL: 'http://localhost:8000/api/v1' }).apiKind).toBe('loopback');
    expect(okConfig({ VITE_PROFILE: 'local', VITE_API_BASE_URL: 'http://127.0.0.1:8000/api/v1' }).apiKind).toBe('loopback');
    expect(okConfig({ VITE_PROFILE: 'local', VITE_API_BASE_URL: 'http://[::1]:8000/api/v1/' }).apiBaseUrl).toBe(
      'http://[::1]:8000/api/v1',
    );
    expect(okConfig({ VITE_PROFILE: 'local', VITE_API_BASE_URL: '/api/v1' }).apiKind).toBe('relative');
  });

  it.each(['local', 'demo', 'escala'] as const)('%s + sin mocks + API no loopback + none → fatal', (profile) => {
    expect(issuesOf({ VITE_PROFILE: profile, VITE_API_BASE_URL: CLOUD_API, VITE_AUTH_MODE: 'none' })).toContain(
      'auth_none_not_allowed',
    );
  });

  it('demo + sin mocks + API loopback + none → fatal (el fallback loopback usa local)', () => {
    expect(issuesOf({ VITE_PROFILE: 'demo', VITE_API_BASE_URL: 'http://localhost:8000/api/v1' })).toContain(
      'auth_none_not_allowed',
    );
  });

  it.each(['local', 'demo', 'escala'] as const)('%s + cognito con isSecureContext=false → fatal', (profile) => {
    expect(issuesOf({ VITE_PROFILE: profile, VITE_API_BASE_URL: CLOUD_API, ...COGNITO }, INSECURE)).toContain(
      'cognito_insecure_context',
    );
  });

  it('escala + mocks → fatal (con cualquier auth)', () => {
    expect(issuesOf({ VITE_PROFILE: 'escala', VITE_USE_MOCKS: 'true' })).toContain('mocks_forbidden_in_escala');
    expect(issuesOf({ VITE_PROFILE: 'escala', VITE_USE_MOCKS: 'true', ...COGNITO })).toContain('mocks_forbidden_in_escala');
  });

  it.each(['demo', 'escala'] as const)('isSecureContext=false fuera de local → fatal (%s)', (profile) => {
    expect(issuesOf({ VITE_PROFILE: profile, VITE_USE_MOCKS: profile === 'demo' ? 'true' : 'false', ...COGNITO, VITE_API_BASE_URL: CLOUD_API }, INSECURE)).toContain(
      'insecure_context',
    );
  });

  it('local fuera de contexto seguro arranca (mocks, sin cognito)', () => {
    expect(okConfig({ VITE_PROFILE: 'local', VITE_USE_MOCKS: 'true' }, INSECURE).profile).toBe('local');
  });
});

describe('resolveProfile — matriz de capacidades §5.2', () => {
  it('demo con mocks (ensayo) + none → OK, con persistencia solo si es sintético', () => {
    const withSynthetic = okConfig({ VITE_PROFILE: 'demo', VITE_USE_MOCKS: 'true', VITE_DATA_CLASSIFICATION: SYNTHETIC });
    expect(withSynthetic.capabilities).toMatchObject({ persistence: true, queue: true, newFamily: true, syntheticBanner: true });
    const noSynthetic = okConfig({ VITE_PROFILE: 'demo', VITE_USE_MOCKS: 'true' });
    expect(noSynthetic.capabilities).toMatchObject({ persistence: false, queue: false });
    expect(noSynthetic.warnings).toContain('persistence_disabled_not_synthetic');
  });

  it('demo cloud exige cognito y queda OK con cognito válido', () => {
    const config = okConfig({ VITE_PROFILE: 'demo', VITE_API_BASE_URL: CLOUD_API, ...COGNITO, VITE_DATA_CLASSIFICATION: SYNTHETIC });
    expect(config.apiKind).toBe('cloud');
    expect(config.capabilities.authMode).toBe('cognito');
    expect(config.cognito).toEqual({
      authority: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_SIMPOOL01',
      domain: 'https://auth.brujula-demo.example',
      clientId: 'simclientid0001',
      scopes: 'openid jardines:read familias:read',
      redirectPath: '/auth/callback',
    });
  });

  it('escala: sin persistencia, sin cola, sin Familia nueva ni banner sintético', () => {
    const config = okConfig({ VITE_PROFILE: 'escala', VITE_API_BASE_URL: CLOUD_API, ...COGNITO, VITE_DATA_CLASSIFICATION: SYNTHETIC });
    expect(config.capabilities).toEqual({
      mocks: false,
      authMode: 'cognito',
      persistence: false,
      queue: false,
      newFamily: false,
      syntheticBanner: false,
      cacheTtlHours: 12,
    });
  });

  it('local: newFamily verdadero; local cloud exige cognito', () => {
    expect(okConfig({ VITE_USE_MOCKS: 'true' }).capabilities.newFamily).toBe(true);
    expect(issuesOf({ VITE_PROFILE: 'local', VITE_API_BASE_URL: CLOUD_API })).toContain('auth_none_not_allowed');
    expect(okConfig({ VITE_PROFILE: 'local', VITE_API_BASE_URL: CLOUD_API, ...COGNITO }).apiKind).toBe('cloud');
  });

  it('TTL: 1–72 entero; inválido usa 12 y avisa', () => {
    expect(okConfig({ VITE_USE_MOCKS: 'true', VITE_DEMO_CACHE_TTL_HOURS: '72' }).capabilities.cacheTtlHours).toBe(72);
    expect(okConfig({ VITE_USE_MOCKS: 'true', VITE_DEMO_CACHE_TTL_HOURS: '1' }).capabilities.cacheTtlHours).toBe(1);
    for (const bad of ['0', '73', '1.5', 'doce', '-1']) {
      const config = okConfig({ VITE_USE_MOCKS: 'true', VITE_DEMO_CACHE_TTL_HOURS: bad });
      expect(config.capabilities.cacheTtlHours).toBe(12);
      expect(config.warnings).toContain('cache_ttl_invalid');
    }
  });
});

describe('resolveProfile — validación de variables §5.1', () => {
  it('perfil, mocks y auth desconocidos → fatal', () => {
    expect(issuesOf({ VITE_PROFILE: 'prod' })).toEqual(['profile_unknown']);
    expect(issuesOf({ VITE_USE_MOCKS: 'yes' })).toContain('mocks_invalid');
    expect(issuesOf({ VITE_USE_MOCKS: 'true', VITE_AUTH_MODE: 'saml' })).toContain('auth_mode_unknown');
  });

  it('sin mocks la API es obligatoria y se valida', () => {
    expect(issuesOf({ VITE_PROFILE: 'local' })).toContain('api_missing');
    for (const bad of [
      'ftp://localhost/api/v1',
      'http://api.brujula-demo.example/api/v1',
      'https://user:pass@api.brujula-demo.example/api/v1',
      'https://api.brujula-demo.example/api/v1?x=1',
      'https://api.brujula-demo.example/api/v1#frag',
      'https://api.brujula-demo.example/otra',
      'no es url',
      '/api/v2',
    ]) {
      expect(issuesOf({ VITE_PROFILE: 'local', VITE_API_BASE_URL: bad, ...COGNITO })).toContain('api_invalid');
    }
    expect(issuesOf({ VITE_PROFILE: 'demo', VITE_API_BASE_URL: '/api/v1', ...COGNITO })).toContain(
      'api_relative_outside_local',
    );
  });

  it('cognito exige authority, dominio, client id, scopes y redirect válidos', () => {
    const base = { VITE_PROFILE: 'demo', VITE_API_BASE_URL: CLOUD_API, ...COGNITO };
    expect(issuesOf({ ...base, VITE_COGNITO_AUTHORITY: 'https://login.brujula-demo.example/pool' })).toContain(
      'cognito_authority_invalid',
    );
    expect(issuesOf({ ...base, VITE_COGNITO_AUTHORITY: `${COGNITO.VITE_COGNITO_AUTHORITY}?x=1` })).toContain(
      'cognito_authority_invalid',
    );
    expect(issuesOf({ ...base, VITE_COGNITO_DOMAIN: 'http://auth.brujula-demo.example' })).toContain('cognito_domain_invalid');
    expect(issuesOf({ ...base, VITE_COGNITO_CLIENT_ID: 'CON-MAYUS' })).toContain('cognito_client_id_invalid');
    expect(issuesOf({ ...base, VITE_COGNITO_SCOPES: '' })).toContain('cognito_scopes_invalid');
    expect(issuesOf({ ...base, VITE_COGNITO_SCOPES: 'openid <script>' })).toContain('cognito_scopes_invalid');
    expect(issuesOf({ ...base, VITE_COGNITO_REDIRECT_PATH: '//evil.example' })).toContain('cognito_redirect_path_invalid');
    expect(okConfig({ ...base, VITE_COGNITO_REDIRECT_PATH: '/auth/otro' }).cognito?.redirectPath).toBe('/auth/otro');
  });

  it('los issues no contienen valores de entrada', () => {
    const result = resolveProfile({ VITE_PROFILE: 'demo', VITE_API_BASE_URL: 'https://secreto.example/api/v1' }, SECURE);
    expect(JSON.stringify(result)).not.toContain('secreto');
  });
});
