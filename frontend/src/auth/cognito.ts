// Adaptador Cognito (DEC-032, §14.1, NIT 15). oidc-client-ts se carga con import() dinámico solo
// cuando VITE_AUTH_MODE=cognito. Tokens solo en memoria; sessionStorage guarda únicamente el
// `state`/PKCE transitorio. Todo AWS es NO_VERIFICADO: no hay pool, dominio ni cliente creados.
import type { CognitoConfig } from '../config/profile';
import type { AuthAdapter, AuthUser } from './adapter';

type OidcModule = typeof import('oidc-client-ts');
type UserManagerLike = InstanceType<OidcModule['UserManager']>;
type OidcUserLike = { access_token: string; expires_at?: number; expired?: boolean };

export interface CognitoAdapterDeps {
  /** Inyectable en pruebas (adaptador simulado, sin red). */
  readonly loadOidc?: () => Promise<OidcModule>;
  readonly origin?: string;
  readonly sessionStorage?: Storage;
}

/** Configuración EXACTA de §14.1 (los defaults se fijan explícitamente). */
export function buildUserManagerSettings(config: CognitoConfig, oidc: OidcModule, origin: string, stateStorage: Storage) {
  return {
    authority: config.authority,
    client_id: config.clientId,
    redirect_uri: `${origin}${config.redirectPath}`,
    scope: config.scopes,
    response_type: 'code', // + PKCE (disablePKCE queda en false)
    userStore: new oidc.WebStorageStateStore({ store: new oidc.InMemoryWebStorage() }), // tokens solo en memoria
    stateStore: new oidc.WebStorageStateStore({ store: stateStorage }), // solo state/PKCE transitorio
    automaticSilentRenew: false,
    monitorSession: false,
    loadUserInfo: false,
    filterProtocolClaims: true,
    fetchRequestCredentials: 'omit' as RequestCredentials,
  };
}

/** NIT 15: logout_uri = location.origin + '/' (debe estar en las allowed sign-out URLs, PREG-032). */
export function buildLogoutUrl(config: CognitoConfig, origin: string): string {
  return `${config.domain}/logout?client_id=${encodeURIComponent(config.clientId)}&logout_uri=${encodeURIComponent(`${origin}/`)}`;
}

function toAuthUser(user: OidcUserLike | null): AuthUser | null {
  if (user === null || typeof user.access_token !== 'string' || user.access_token === '') return null;
  return { accessToken: user.access_token, expiresAt: typeof user.expires_at === 'number' ? user.expires_at : null };
}

export function createCognitoAdapter(config: CognitoConfig, deps: CognitoAdapterDeps = {}): AuthAdapter {
  const loadOidc = deps.loadOidc ?? (() => import('oidc-client-ts'));
  const origin = deps.origin ?? window.location.origin;
  let managerPromise: Promise<UserManagerLike> | null = null;

  const manager = (): Promise<UserManagerLike> => {
    managerPromise ??= loadOidc().then((oidc) => {
      const storage = deps.sessionStorage ?? window.sessionStorage;
      return new oidc.UserManager(buildUserManagerSettings(config, oidc, origin, storage));
    });
    return managerPromise;
  };

  return {
    mode: 'cognito',
    async init() {
      await (await manager()).clearStaleState();
    },
    async getUser() {
      const user = (await (await manager()).getUser()) as OidcUserLike | null;
      if (user === null || user.expired === true) return null;
      return toAuthUser(user);
    },
    async signinCallback() {
      const user = (await (await manager()).signinCallback()) as (OidcUserLike & { state?: unknown }) | undefined;
      const authUser = toAuthUser(user ?? null);
      if (authUser === null) throw new Error('auth_callback_no_user');
      const state = user?.state as { returnTo?: unknown } | undefined;
      return { user: authUser, returnTo: state?.returnTo };
    },
    async signinRedirect(returnTo: string) {
      await (await manager()).signinRedirect({ state: { returnTo } });
    },
    async removeUser() {
      await (await manager()).removeUser();
    },
    onAccessTokenExpired(listener) {
      let unsubscribe: (() => void) | null = null;
      let cancelled = false;
      void manager().then((m) => {
        if (cancelled) return;
        m.events.addAccessTokenExpired(listener);
        unsubscribe = () => m.events.removeAccessTokenExpired(listener);
      });
      return () => {
        cancelled = true;
        unsubscribe?.();
      };
    },
    logoutUrl() {
      return buildLogoutUrl(config, origin);
    },
  };
}
