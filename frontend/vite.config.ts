/// <reference types="vitest/config" />
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';
import c3Meta from './src/api/generated/c3.meta.json' with { type: 'json' };
import { COPY_CATALOG } from './src/i18n/catalog.ts';
import { MOCK_COPY } from './src/i18n/es.mock.ts';
import { brujulaContent, type Profile } from './vite-plugins/brujula-content.ts';
import { cspPlugin, isLoopbackHttpUrl } from './vite-plugins/csp.ts';

/**
 * Variables públicas que la app lee. Se fijan SIEMPRE vía `define` (con '' si no
 * vienen) para que el reemplazo sea estático y Rolldown elimine el import()
 * dinámico de los mocks en builds sin mocks (§3, V-15).
 */
const VITE_KEYS = [
  'VITE_PROFILE',
  'VITE_USE_MOCKS',
  'VITE_API_BASE_URL',
  'VITE_AUTH_MODE',
  'VITE_COGNITO_AUTHORITY',
  'VITE_COGNITO_DOMAIN',
  'VITE_COGNITO_CLIENT_ID',
  'VITE_COGNITO_SCOPES',
  'VITE_COGNITO_REDIRECT_PATH',
  'VITE_DATA_CLASSIFICATION',
  'VITE_DEMO_CACHE_TTL_HOURS',
  'VITE_PROPOSAL_ADD_INFO',
] as const;

const SYNTHETIC = 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON';

/** Presets de modo (§5.3): no se pueden versionar archivos .env.*. */
const MODE_PRESETS: Readonly<Record<string, Readonly<Record<string, string>>>> = {
  mock: { VITE_PROFILE: 'local', VITE_USE_MOCKS: 'true', VITE_AUTH_MODE: 'none', VITE_DATA_CLASSIFICATION: SYNTHETIC },
  e2e: { VITE_PROFILE: 'local', VITE_USE_MOCKS: 'true', VITE_AUTH_MODE: 'none', VITE_DATA_CLASSIFICATION: SYNTHETIC },
  'demo-rehearsal': {
    VITE_PROFILE: 'demo',
    VITE_USE_MOCKS: 'true',
    VITE_AUTH_MODE: 'none',
    VITE_DATA_CLASSIFICATION: SYNTHETIC,
    BRUJULA_ALLOW_MOCK_COPY: 'true',
  },
  // API real de Rol 2 en loopback vía el proxy de dev (/api/v1 → BRUJULA_DEV_API_PROXY), sin Cognito.
  // `local` es el perfil del fallback loopback (NIT 4) con las mismas capacidades Demo (caché/cola sintética).
  api: {
    VITE_PROFILE: 'local',
    VITE_USE_MOCKS: 'false',
    VITE_API_BASE_URL: '/api/v1',
    VITE_AUTH_MODE: 'none',
    VITE_DATA_CLASSIFICATION: SYNTHETIC,
  },
};

/** Puerto por defecto del backend local de Rol 2 si no se indica BRUJULA_DEV_API_PROXY (modo `api`). */
const DEFAULT_API_PROXY = 'http://127.0.0.1:8000';

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(frontendDir, '..');

function toProfile(value: string | undefined): Profile {
  // Un valor desconocido no decide la política de copy aquí: la app lo rechaza en
  // runtime (ConfigErrorPage). Para el build se trata como el perfil más estricto.
  if (value === undefined || value === '' || value === 'local') return 'local';
  if (value === 'demo') return 'demo';
  return 'escala';
}

export default defineConfig(({ command, mode }) => {
  const env: Record<string, string | undefined> = {
    ...loadEnv(mode, frontendDir, ['VITE_', 'BRUJULA_']),
    ...MODE_PRESETS[mode],
  };
  const profile = toProfile(env.VITE_PROFILE);
  const allowMock = env.BRUJULA_ALLOW_MOCK_COPY === 'true';
  // Las pruebas unitarias (mode 'test') son herméticas: sin BRUJULA_CONTENT_DIR explícito usan
  // siempre el copy mock y no dependen de que ../content exista en la rama.
  const defaultContentDir = mode === 'test' ? '__sin_contenido_en_pruebas__' : '../content';
  // path.resolve acepta rutas relativas a frontend/ y absolutas de Windows (con espacios).
  const contentDir = path.resolve(frontendDir, env.BRUJULA_CONTENT_DIR ?? defaultContentDir);
  const schemaC4Path = path.resolve(repoRoot, '.kiro/specs/_shared/contracts/C4-contenido-manifest.schema.json');

  const define = Object.fromEntries(VITE_KEYS.map((key) => [`import.meta.env.${key}`, JSON.stringify(env[key] ?? '')]));

  const proxyTarget = env.BRUJULA_DEV_API_PROXY ?? (mode === 'api' ? DEFAULT_API_PROXY : undefined);
  if (command === 'serve' && proxyTarget !== undefined && !isLoopbackHttpUrl(proxyTarget)) {
    console.warn('[brujula] BRUJULA_DEV_API_PROXY debe ser una URL loopback (http://127.0.0.1:<puerto>); proxy desactivado.');
  }
  const proxy =
    command === 'serve' && proxyTarget !== undefined && isLoopbackHttpUrl(proxyTarget)
      ? { '/api/v1': { target: proxyTarget, changeOrigin: false } }
      : undefined;

  return {
    plugins: [
      brujulaContent({
        contentDir,
        schemaC4Path,
        c3Meta,
        catalog: COPY_CATALOG,
        mockValues: MOCK_COPY,
        profile,
        allowMock,
        mocks: env.VITE_USE_MOCKS === 'true',
      }),
      react(),
      tailwindcss(),
      cspPlugin({
        apiBaseUrl: env.VITE_API_BASE_URL,
        cognitoAuthority: env.VITE_COGNITO_AUTHORITY,
        cognitoDomain: env.VITE_COGNITO_DOMAIN,
      }),
      // PWA instalable (design.md §12.1): precache solo del app shell; NINGUNA respuesta de API
      // pasa por el service worker (runtimeCaching vacío y /api/ fuera del fallback de navegación).
      VitePWA({
        strategies: 'generateSW',
        registerType: 'prompt',
        injectRegister: null,
        manifest: {
          name: MOCK_COPY['app.name'],
          short_name: MOCK_COPY['app.name'],
          description: MOCK_COPY['app.tagline'],
          lang: 'es-CL',
          start_url: '/',
          scope: '/',
          display: 'standalone',
          theme_color: '#A63D1C',
          background_color: '#FFF8F0',
          icons: [{ src: '/icons/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,svg,webmanifest}'],
          navigateFallback: 'index.html',
          navigateFallbackDenylist: [/^\/api\//],
          runtimeCaching: [],
          cleanupOutdatedCaches: true,
        },
        devOptions: { enabled: false },
      }),
    ],
    define,
    server: {
      fs: { allow: [repoRoot] },
      ...(proxy ? { proxy } : {}),
    },
    build: {
      sourcemap: false,
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['src/test/setup.ts'],
      testTimeout: 20_000,
      include: ['src/**/*.test.{ts,tsx}', 'vite-plugins/**/*.test.ts'],
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  };
});
