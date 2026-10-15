// Núcleo de sesión (design.md §14.1, SUP-037). Máquina de estados explícita, store para
// useSyncExternalStore. El access token vive solo en este closure (memoria), nunca en el estado
// observable ni en storage. Sin UI: AuthProvider/RequireSession llegan en FEAT-003.
import { nowMs } from '../lib/now';
import type { AuthAdapter, AuthUser } from './adapter';
import { sanitizeReturnTo } from './returnTo';

export type AnonymousReason = 'start' | 'expired' | 'callback_error' | 'logout';

export type SessionState =
  | { readonly status: 'none' }
  | { readonly status: 'anonymous'; readonly reason: AnonymousReason }
  | { readonly status: 'authenticating' }
  | { readonly status: 'authenticated'; readonly expiresAt: number | null };

/** Decisión de la puerta de sesión del transporte (§6.2). */
export type AccessTokenDecision =
  | { readonly kind: 'none' }
  | { readonly kind: 'bearer'; readonly token: string }
  | { readonly kind: 'denied' };

/** Lo mínimo que el transporte necesita de la sesión. */
export interface SessionPort {
  getAccessToken(): AccessTokenDecision;
  /** Señal de sesión vigente: se aborta en el logout de esta u otra pestaña (§12.5). */
  signal(): AbortSignal;
}

export interface StartLocation {
  readonly pathname: string;
}

export interface StartResult {
  /** Solo tras un callback OIDC exitoso: ruta saneada a la que volver con replace. */
  readonly returnTo: string | null;
}

export interface Session extends SessionPort {
  readonly authMode: 'none' | 'cognito';
  getState(): SessionState;
  subscribe(listener: () => void): () => void;
  /** Arranque §14.1: callback → authenticating; si no, getUser → authenticated | anonymous('start'). */
  start(location: StartLocation, redirectPath: string): Promise<StartResult>;
  setAuthenticated(user: AuthUser): void;
  toAnonymous(reason: AnonymousReason): void;
  /** Aborta la señal de sesión vigente (logout propio o remoto). */
  abortSignal(): void;
  /** Crea una señal nueva si la vigente está abortada (logout abortado). */
  renewSignal(): void;
  /** Inicia el login por redirección (solo cognito); `returnTo` se sanea antes. */
  login(returnTo: string): Promise<void>;
  /** Suelta el usuario del adaptador y deja la sesión `anonymous('logout')`. */
  removeUser(): Promise<void>;
  /** URL de logout del proveedor (Cognito) o null con `none`. */
  logoutUrl(): string | null;
}

const NONE_STATE: SessionState = Object.freeze({ status: 'none' });

export function createSession(adapter: AuthAdapter): Session {
  const authMode = adapter.mode;
  let state: SessionState = authMode === 'none' ? NONE_STATE : { status: 'anonymous', reason: 'start' };
  let accessToken: string | null = null;
  let controller = new AbortController();
  let unsubscribeExpired: (() => void) | null = null;
  const listeners = new Set<() => void>();

  const setState = (next: SessionState) => {
    state = next;
    for (const listener of [...listeners]) listener();
  };

  const toAnonymous = (reason: AnonymousReason) => {
    if (authMode === 'none') return; // `none` es fijo
    accessToken = null;
    setState({ status: 'anonymous', reason });
  };

  const setAuthenticated = (user: AuthUser) => {
    if (authMode === 'none') return;
    accessToken = user.accessToken;
    setState({ status: 'authenticated', expiresAt: user.expiresAt });
  };

  const isExpired = (expiresAt: number | null) => expiresAt !== null && expiresAt * 1000 <= nowMs();

  return {
    authMode,
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    signal: () => controller.signal,
    abortSignal() {
      if (!controller.signal.aborted) controller.abort(new DOMException('session', 'AbortError'));
    },
    renewSignal() {
      if (controller.signal.aborted) controller = new AbortController();
    },
    getAccessToken(): AccessTokenDecision {
      if (authMode === 'none') return { kind: 'none' };
      if (state.status !== 'authenticated' || accessToken === null) return { kind: 'denied' };
      if (isExpired(state.expiresAt)) {
        toAnonymous('expired');
        return { kind: 'denied' };
      }
      return { kind: 'bearer', token: accessToken };
    },
    setAuthenticated,
    toAnonymous,
    async start(location, redirectPath) {
      if (authMode === 'none') return { returnTo: null };
      await adapter.init();
      unsubscribeExpired?.();
      unsubscribeExpired = adapter.onAccessTokenExpired(() => {
        void adapter.removeUser().finally(() => toAnonymous('expired'));
      });
      if (location.pathname === redirectPath) {
        setState({ status: 'authenticating' });
        try {
          const result = await adapter.signinCallback();
          setAuthenticated(result.user);
          return { returnTo: sanitizeReturnTo(result.returnTo) };
        } catch {
          toAnonymous('callback_error');
          return { returnTo: null };
        }
      }
      try {
        const user = await adapter.getUser();
        if (user !== null && !isExpired(user.expiresAt)) setAuthenticated(user);
        else toAnonymous('start');
      } catch {
        toAnonymous('start');
      }
      return { returnTo: null };
    },
    async login(returnTo) {
      if (authMode === 'none') return;
      await adapter.signinRedirect(sanitizeReturnTo(returnTo));
    },
    async removeUser() {
      accessToken = null;
      try {
        await adapter.removeUser();
      } finally {
        toAnonymous('logout');
      }
    },
    logoutUrl: () => (authMode === 'none' ? null : adapter.logoutUrl()),
  };
}

// --- Sesión activa del proceso (main.tsx la instala una vez) ---

let active: Session | null = null;

export function installSession(session: Session): void {
  active = session;
}

export function getSession(): Session {
  if (active === null) throw new Error('session_missing');
  return active;
}

export function resetSessionForTests(): void {
  active = null;
}
