// Adaptador sin autenticación: solo válido con mocks o API loopback en `local` (§5.2, NIT 4).
// La sesión queda fija en `none` y el transporte no agrega Authorization.
import type { AuthAdapter } from './adapter';

export function createNoneAdapter(): AuthAdapter {
  return {
    mode: 'none',
    init: async () => {},
    getUser: async () => null,
    signinCallback: async () => {
      throw new Error('auth_none_no_callback');
    },
    signinRedirect: async () => {},
    removeUser: async () => {},
    onAccessTokenExpired: () => () => {},
    logoutUrl: () => null,
  };
}
