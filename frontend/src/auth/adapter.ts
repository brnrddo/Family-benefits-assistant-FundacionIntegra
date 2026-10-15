// Contrato del adaptador de autenticación (DEC-032, §14.1). `none` es el valor por defecto;
// `cognito` (oidc-client-ts, code + PKCE) queda desplegable pero desactivado y NO_VERIFICADO.

export interface AuthUser {
  /** Access token (nunca el de identidad). Vive solo en memoria. */
  readonly accessToken: string;
  /** Vencimiento en segundos epoch, si el proveedor lo informa. */
  readonly expiresAt: number | null;
}

export interface SigninCallbackResult {
  readonly user: AuthUser;
  /** `returnTo` crudo del `state` OIDC; session.ts lo sanea con returnTo.ts. */
  readonly returnTo: unknown;
}

export interface AuthAdapter {
  readonly mode: 'none' | 'cognito';
  /** Limpieza de arranque (Cognito: `clearStaleState`). */
  init(): Promise<void>;
  getUser(): Promise<AuthUser | null>;
  signinCallback(): Promise<SigninCallbackResult>;
  signinRedirect(returnTo: string): Promise<void>;
  removeUser(): Promise<void>;
  /** Suscripción al vencimiento del access token; devuelve la desuscripción. */
  onAccessTokenExpired(listener: () => void): () => void;
  /** URL de logout del proveedor (Cognito Hosted UI) o null. */
  logoutUrl(): string | null;
}
