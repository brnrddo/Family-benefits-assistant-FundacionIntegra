// Smoke e2e a 360 px con mocks C3 sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON): Inicio → Ficha →
// Tarjeta → Conversación (3 toques) → Avance → Asistente (+ Familia nueva). Guarda una captura PNG por
// vista en SCREENSHOT_DIR (por defecto .agents/tasks/frontend-pwa/screenshots) y corre axe en Inicio
// y Ficha (0 violaciones critical/serious). Sin llamadas de red reales: el mock vive en la página.
/// <reference lib="dom" />
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MOCK_COPY } from '../src/i18n/es.mock.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = process.env.SCREENSHOT_DIR ?? path.resolve(here, '../../.agents/tasks/frontend-pwa/screenshots');
const C = MOCK_COPY;

async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(360);
}

async function expectAxeClean(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const blocking = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
  expect(blocking.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

/**
 * Captura de la vista completa. En vez de `fullPage` (que deja la barra fija a media página) se
 * agranda la ventana al alto del documento y luego se restaura 360×800.
 */
async function shot(page: Page, name: string): Promise<void> {
  await expectNoHorizontalScroll(page);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: 360, height: Math.max(800, height) });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`) });
  await page.setViewportSize({ width: 360, height: 800 });
}

test('recorrido principal a 360 px', async ({ page }) => {
  const cspErrors: string[] = [];
  page.on('console', (message) => {
    if (message.text().includes('Content Security Policy')) cspErrors.push(message.type());
  });
  page.on('dialog', (dialog) => void dialog.dismiss());

  // Inicio
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: C['home.title'] })).toBeVisible();
  await expect(page.getByText(C['home.progress'].replace('{informed}', '2').replace('{total}', '8'))).toBeVisible();
  await expectAxeClean(page);
  await shot(page, 'b01-inicio');

  // Ficha (1 toque desde Inicio: la siguiente familia)
  await page.locator('[data-primary-action]').click();
  await expect(page.getByRole('heading', { level: 1, name: 'Familia FAM-SIM-E3-00001' })).toBeVisible();
  await expect(page.getByText(C['card.why_first_label']).first()).toBeVisible();
  await expectAxeClean(page);
  await shot(page, 'b02-ficha');

  // Tarjeta (mensaje + CARD_V1)
  await page.getByRole('link', { name: C['family.actions.message'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['message.title'] })).toBeVisible();
  await expect(page.locator('[data-print-root]')).toBeVisible();
  await shot(page, 'b03-tarjeta');
  await page.getByRole('link', { name: C['nav.back'], exact: true }).click();

  // Conversación en exactamente 3 toques
  await page.getByRole('link', { name: C['family.actions.mark'] }).click(); // toque 1
  await expect(page.getByRole('heading', { level: 1, name: C['conversation.title'] })).toBeVisible();
  await expect(page.getByRole('button', { name: C['conversation.confirm'] })).toBeDisabled();
  await shot(page, 'b04-conversacion');
  await page.locator('label', { hasText: C['next_step.go_to_institution'] }).click(); // toque 2
  await page.getByRole('button', { name: C['conversation.confirm'] }).click(); // toque 3
  await expect(page.getByText(C['conversation.success'])).toBeVisible();
  await shot(page, 'b05-conversacion-registrada');

  // Avance: sube SOLO con el dato del servidor (2 → 3 de 8 en el jardín)
  await page.getByRole('link', { name: C['nav.kpi'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['kpi.title'] })).toBeVisible();
  await expect(page.getByText(C['kpi.ratio'].replace('{informed}', '3').replace('{total}', '8'))).toBeVisible();
  await expect(page.locator('[data-primary-action]')).toHaveCount(0);
  await shot(page, 'b06-avance');

  // Asistente: pregunta de ejemplo → respuesta CATALOG_INFO con citas
  await page.getByRole('link', { name: C['nav.assistant'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['assistant.title'] })).toBeVisible();
  await page.getByRole('button', { name: C['assistant.example.1'] }).click();
  await page.getByRole('button', { name: C['assistant.submit'], exact: true }).click();
  await expect(page.getByRole('heading', { name: C['assistant.answer_title'] })).toBeVisible();
  await expect(page.getByRole('link', { name: /SRC-SIM-001/ })).toHaveAttribute('href', /^https:\/\//);
  await shot(page, 'b07-asistente');

  // Familia nueva (paso 1)
  await page.getByRole('link', { name: C['nav.new_family'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['new_family.title'] })).toBeVisible();
  await shot(page, 'b08-familia-nueva');

  expect(cspErrors).toEqual([]);
});
