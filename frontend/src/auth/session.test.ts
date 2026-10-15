// Núcleo de sesión (§14.1) con adaptador cognito SIMULADO: sin red ni Cognito real (NO_VERIFICADO).
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CognitoConfig } from '../config/profile';
import { resetClock, setClock } from '../lib/now';
import type { AuthAdapter, AuthUser, SigninCallbackResult } from './adapter';
import { buildLogoutUrl, buildUserManagerSettings, createCognitoAdapter } from './cognito';
import { createNoneAdapter } from './none';
import { createSession } from './session';

const NOW = Date.parse('2026-10-14T13:00:00Z');
const FUTURE = NOW / 1000 + 3600;
const PAST = NOW / 1000 - 1;

const COGNITO: CognitoConfig = {
  authority: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_SIMPOOL01',
  domain: 'https://auth.brujula-demo.example',
  clientId: 'simclientid0001',
  scopes: 'openid jardines:read',
  redirectPath: '/auth/callback',
};

function fakeCognitoAdapter(options: { user?: AuthUser | null; callback?: SigninCallbackResult | Error } = {}) {
  const expiredListeners = new Set<() => void>();
  const adapter: AuthAdapter & { fireExpired(): void } = {
    mode: 'cognito',
    init: vi.fn(async () => {}),
    getUser: vi.fn(async () => options.user ?? null),
    signinCallback: vi.fn(async () => {
      if (options.callback instanceof Error) throw options.callback;
      if (options.callback === undefined) throw new Error('sin callback');
      return options.callback;
    }),
    signinRedirect: vi.fn(async () => {}),
    removeUser: vi.fn(async () => {}),
    onAccessTokenExpired: (listener) => {
      expiredListeners.add(listener);
      return () => expiredListeners.delete(listener);
    },
    logoutUrl: () => buildLogoutUrl(COGNITO, 'https://pwa.brujula-demo.example'),
    fireExpired: () => expiredListeners.forEach((l) => l()),
  };
  return adapter;
}

describe('auth/session — núcleo', () => {
  afterEach(() => resetClock());

  it('authMode none: estado fijo `none`, sin header y sin transiciones', async () => {
    const session = createSession(createNoneAdapter());
    expect(session.getState()).toEqual({ status: 'none' });
    expect(session.getAccessToken()).toEqual({ kind: 'none' });
    session.toAnonymous('expired');
    await session.start({ pathname: '/' }, '/auth/callback');
    expect(session.getState()).toEqual({ status: 'none' });
  });

  it('cognito: arranca anonymous(start) sin usuario y la puerta deniega', async () => {
    const adapter = fakeCognitoAdapter();
    const session = createSession(adapter);
    await session.start({ pathname: '/' }, '/auth/callback');
    expect(adapter.init).toHaveBeenCalledOnce();
    expect(session.getState()).toEqual({ status: 'anonymous', reason: 'start' });
    expect(session.getAccessToken()).toEqual({ kind: 'denied' });
  });

  it('cognito: getUser no vencido → authenticated con Bearer; el token no está en el estado observable', async () => {
    setClock(() => NOW);
    const session = createSession(fakeCognitoAdapter({ user: { accessToken: 'tok-sim-1', expiresAt: FUTURE } }));
    await session.start({ pathname: '/' }, '/auth/callback');
    expect(session.getState()).toEqual({ status: 'authenticated', expiresAt: FUTURE });
    expect(JSON.stringify(session.getState())).not.toContain('tok-sim-1');
    expect(session.getAccessToken()).toEqual({ kind: 'bearer', token: 'tok-sim-1' });
  });

  it('token vencido localmente → anonymous(expired) y denied', async () => {
    setClock(() => NOW);
    const session = createSession(fakeCognitoAdapter());
    session.setAuthenticated({ accessToken: 'tok-sim-2', expiresAt: PAST });
    expect(session.getAccessToken()).toEqual({ kind: 'denied' });
    expect(session.getState()).toEqual({ status: 'anonymous', reason: 'expired' });
  });

  it('addAccessTokenExpired → removeUser → anonymous(expired)', async () => {
    setClock(() => NOW);
    const adapter = fakeCognitoAdapter({ user: { accessToken: 'tok-sim-3', expiresAt: FUTURE } });
    const session = createSession(adapter);
    await session.start({ pathname: '/' }, '/auth/callback');
    adapter.fireExpired();
    await vi.waitFor(() => expect(session.getState()).toEqual({ status: 'anonymous', reason: 'expired' }));
    expect(adapter.removeUser).toHaveBeenCalled();
  });

  it('callback ok → authenticated y returnTo saneado; hostil → /', async () => {
    setClock(() => NOW);
    const ok = createSession(
      fakeCognitoAdapter({ callback: { user: { accessToken: 'tok-sim-4', expiresAt: FUTURE }, returnTo: '/familias/FAM-SIM-E3-00001/conversacion' } }),
    );
    await expect(ok.start({ pathname: '/auth/callback' }, '/auth/callback')).resolves.toEqual({
      returnTo: '/familias/FAM-SIM-E3-00001/conversacion',
    });
    expect(ok.getState().status).toBe('authenticated');
    const hostile = createSession(
      fakeCognitoAdapter({ callback: { user: { accessToken: 'tok-sim-5', expiresAt: FUTURE }, returnTo: '//evil.example' } }),
    );
    await expect(hostile.start({ pathname: '/auth/callback' }, '/auth/callback')).resolves.toEqual({ returnTo: '/' });
  });

  it('callback fallido → anonymous(callback_error), pasando por authenticating', async () => {
    const session = createSession(fakeCognitoAdapter({ callback: new Error('state inválido') }));
    const seen: string[] = [];
    session.subscribe(() => seen.push(session.getState().status));
    await session.start({ pathname: '/auth/callback' }, '/auth/callback');
    expect(seen[0]).toBe('authenticating');
    expect(session.getState()).toEqual({ status: 'anonymous', reason: 'callback_error' });
  });

  it('señal de sesión: abortSignal aborta, renewSignal crea una nueva', () => {
    const session = createSession(fakeCognitoAdapter());
    const first = session.signal();
    session.abortSignal();
    expect(first.aborted).toBe(true);
    session.renewSignal();
    expect(session.signal()).not.toBe(first);
    expect(session.signal().aborted).toBe(false);
  });

  it('login sanea returnTo; removeUser deja anonymous(logout)', async () => {
    const adapter = fakeCognitoAdapter();
    const session = createSession(adapter);
    await session.login('https://evil.example');
    expect(adapter.signinRedirect).toHaveBeenCalledWith('/');
    session.setAuthenticated({ accessToken: 'tok-sim-6', expiresAt: null });
    await session.removeUser();
    expect(session.getState()).toEqual({ status: 'anonymous', reason: 'logout' });
    expect(session.getAccessToken()).toEqual({ kind: 'denied' });
  });
});

describe('auth/cognito — adaptador con oidc-client-ts simulado', () => {
  class FakeStore {
    readonly options: { store: unknown };
    constructor(options: { store: unknown }) {
      this.options = options;
    }
  }
  class FakeInMemory {}
  const created: { settings: Record<string, unknown> }[] = [];
  class FakeUserManager {
    readonly events = { addAccessTokenExpired: vi.fn(), removeAccessTokenExpired: vi.fn() };
    clearStaleState = vi.fn(async () => {});
    getUser = vi.fn(async () => ({ access_token: 'tok-sim-7', expires_at: FUTURE, expired: false }));
    signinRedirect = vi.fn(async () => {});
    signinCallback = vi.fn(async () => ({ access_token: 'tok-sim-8', expires_at: FUTURE, state: { returnTo: '/avance' } }));
    removeUser = vi.fn(async () => {});
    readonly settings: Record<string, unknown>;
    constructor(settings: Record<string, unknown>) {
      this.settings = settings;
      created.push(this);
    }
  }
  const fakeModule = {
    UserManager: FakeUserManager,
    WebStorageStateStore: FakeStore,
    InMemoryWebStorage: FakeInMemory,
  } as unknown as typeof import('oidc-client-ts');

  it('configuración EXACTA de §14.1 (tokens en memoria, state en sessionStorage)', () => {
    const settings = buildUserManagerSettings(COGNITO, fakeModule, 'https://pwa.brujula-demo.example', window.sessionStorage);
    expect(settings).toMatchObject({
      authority: COGNITO.authority,
      client_id: COGNITO.clientId,
      redirect_uri: 'https://pwa.brujula-demo.example/auth/callback',
      scope: 'openid jardines:read',
      response_type: 'code',
      automaticSilentRenew: false,
      monitorSession: false,
      loadUserInfo: false,
      filterProtocolClaims: true,
      fetchRequestCredentials: 'omit',
    });
    expect((settings.userStore as unknown as FakeStore).options.store).toBeInstanceOf(FakeInMemory);
    expect((settings.stateStore as unknown as FakeStore).options.store).toBe(window.sessionStorage);
    expect(settings).not.toHaveProperty('disablePKCE');
    expect(settings).not.toHaveProperty('client_secret');
  });

  it('NIT 15: logout a VITE_COGNITO_DOMAIN/logout con logout_uri = origin + /', () => {
    expect(buildLogoutUrl(COGNITO, 'http://localhost:4173')).toBe(
      'https://auth.brujula-demo.example/logout?client_id=simclientid0001&logout_uri=http%3A%2F%2Flocalhost%3A4173%2F',
    );
  });

  it('import dinámico diferido, clearStaleState al iniciar y returnTo desde el state', async () => {
    const loadOidc = vi.fn(async () => fakeModule);
    const adapter = createCognitoAdapter(COGNITO, { loadOidc, origin: 'https://pwa.brujula-demo.example', sessionStorage: window.sessionStorage });
    expect(loadOidc).not.toHaveBeenCalled();
    await adapter.init();
    expect(loadOidc).toHaveBeenCalledOnce();
    const manager = created.at(-1) as unknown as FakeUserManager;
    expect(manager.clearStaleState).toHaveBeenCalledOnce();
    await expect(adapter.getUser()).resolves.toEqual({ accessToken: 'tok-sim-7', expiresAt: FUTURE });
    await expect(adapter.signinCallback()).resolves.toEqual({
      user: { accessToken: 'tok-sim-8', expiresAt: FUTURE },
      returnTo: '/avance',
    });
    await adapter.signinRedirect('/avance');
    expect(manager.signinRedirect).toHaveBeenCalledWith({ state: { returnTo: '/avance' } });
    const off = adapter.onAccessTokenExpired(() => {});
    await vi.waitFor(() => expect(manager.events.addAccessTokenExpired).toHaveBeenCalled());
    off();
    expect(manager.events.removeAccessTokenExpired).toHaveBeenCalled();
    expect(loadOidc).toHaveBeenCalledOnce();
  });
});
