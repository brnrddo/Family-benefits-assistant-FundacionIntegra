// Arranque (design.md §5.2, §14.1): (1) resolveProfile ANTES de montar; si falla, ConfigErrorPage
// sin ninguna llamada a la API. (2) Sesión none|cognito. (3) Transporte real o mocks en proceso
// (import() dinámico detrás de VITE_USE_MOCKS: en builds sin mocks msw no entra al bundle).
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { createFetchTransport, setTransport } from './api/transport';
import App from './App';
import { createCognitoAdapter } from './auth/cognito';
import { createNoneAdapter } from './auth/none';
import { createSession, installSession } from './auth/session';
import { configureRuntime, DEFAULT_REDIRECT_PATH, readViteEnv, resolveProfile } from './config/profile';
import { createAppQueryClient } from './data/queryClient';
import { startDataSync } from './data/sync';
import { ConfigErrorPage } from './features/system/ConfigErrorPage';
import { t } from './i18n/copy';
import { log } from './lib/log';
import { toastStore } from './ui/toastStore';

/** Service worker de la PWA (solo builds de producción). Precachea solo el app shell (runtimeCaching: []). */
function registerServiceWorker(): void {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
  void import('virtual:pwa-register')
    .then(({ registerSW }) => {
      const updateSW = registerSW({
        immediate: true,
        onNeedRefresh() {
          toastStore.push(t('app.update_available'), { label: t('app.update_action'), run: () => void updateSW(true) });
        },
      });
    })
    .catch(() => log.warn({ kind: 'sw_register_failed' }));
}

async function bootstrap(): Promise<void> {
  const container = document.getElementById('root');
  if (container === null) return;
  const root = createRoot(container);

  const result = resolveProfile(readViteEnv(), { isSecureContext: window.isSecureContext });
  if (!result.ok) {
    log.error({ kind: 'config', issues: result.issues });
    root.render(<ConfigErrorPage />);
    return;
  }
  const config = result.config;
  configureRuntime(config);

  const adapter = config.cognito !== null ? createCognitoAdapter(config.cognito) : createNoneAdapter();
  const session = createSession(adapter);
  installSession(session);

  const baseUrl = new URL(config.apiBaseUrl, window.location.origin).href.replace(/\/$/, '');
  if (import.meta.env.VITE_USE_MOCKS === 'true' && config.capabilities.mocks) {
    const { startBrowserMocks } = await import('./mocks/transport');
    setTransport(startBrowserMocks({ session, baseUrl, search: window.location.search }).transport);
  } else {
    setTransport(createFetchTransport({ baseUrl, session }));
  }

  // Ninguna llamada a la API ocurre antes de este paso (§14.1).
  const { returnTo } = await session.start(
    { pathname: window.location.pathname },
    config.cognito?.redirectPath ?? DEFAULT_REDIRECT_PATH,
  );
  if (returnTo !== null) window.history.replaceState(null, '', returnTo);

  // DEC-047: nombres de trato INVENTADOS precargados solo en Demo, directo a IndexedDB (sin red).
  // La condición estática sobre VITE_PROFILE deja el módulo y su JSON fuera del build `escala`.
  if (import.meta.env.VITE_PROFILE !== 'escala' && config.capabilities.localNames) {
    try {
      const { seedLocalNames } = await import('./offline/localNamesSeed');
      await seedLocalNames();
    } catch {
      log.warn({ kind: 'local_names_seed_failed' });
    }
  }

  const queryClient = createAppQueryClient();
  await startDataSync(queryClient);
  registerServiceWorker();

  root.render(
    <StrictMode>
      <App queryClient={queryClient} />
    </StrictMode>,
  );
}

void bootstrap();
