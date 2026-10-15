// Puerta de sesión en la UI (design.md §14.1, SUP-037, simplificada). Con `none` no hay login.
// Con Cognito sin sesión: online → LoginRequired; offline con persistencia Demo → caché de solo lectura.
import { useSyncExternalStore, type ReactNode } from 'react';
import { useLocation } from 'react-router';
import { runtimeConfig } from '../config/profile';
import { t } from '../i18n/copy';
import { useOnline } from '../offline/network';
import { Button } from '../ui/Button';
import { PageTitle } from '../ui/PageTitle';
import { Skeleton } from '../ui/states';
import { getSession, type SessionState } from './session';

function useSessionState(): SessionState {
  const session = getSession();
  return useSyncExternalStore(session.subscribe, session.getState, session.getState);
}

export function LoginRequired({ expired }: { readonly expired: boolean }) {
  const location = useLocation();
  return (
    <section className="space-y-4">
      <PageTitle>{t('auth.login_required.title')}</PageTitle>
      <p>{expired ? t('auth.session_expired') : t('auth.login_required.body')}</p>
      <Button icon="user" data-primary-action onClick={() => void getSession().login(`${location.pathname}${location.search}`)}>
        {t('auth.login')}
      </Button>
    </section>
  );
}

export function RequireSession({ children }: { readonly children: ReactNode }) {
  const state = useSessionState();
  const online = useOnline();
  if (state.status === 'none' || state.status === 'authenticated') return children;
  if (state.status === 'authenticating') return <Skeleton rows={2} />;
  if (!online && runtimeConfig().capabilities.persistence) return children;
  return <LoginRequired expired={state.reason === 'expired'} />;
}
