// e2e smoke (design.md §19, alcance simplificado DEC-033): solo Chromium a 360×800, es-CL, contra
// el build `e2e` (perfil local + mocks C3 sintéticos en proceso) servido por `vite preview`.
import { defineConfig } from '@playwright/test';

const PORT = 4173;

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  timeout: 60_000,
  use: {
    browserName: 'chromium',
    baseURL: `http://localhost:${PORT}`,
    viewport: { width: 360, height: 800 },
    deviceScaleFactor: 1,
    locale: 'es-CL',
    timezoneId: 'America/Santiago',
    serviceWorkers: 'block',
  },
  webServer: {
    command: 'npm run build:e2e && npm run preview',
    url: `http://localhost:${PORT}`,
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
