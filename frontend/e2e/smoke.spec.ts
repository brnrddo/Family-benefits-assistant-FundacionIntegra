// Smoke e2e a 360 px con mocks C3 sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON): Inicio (orden neutro
// alfabético + acciones prioritarias, DEC-037) → Ficha (dos grupos de beneficios) → nombre de trato
// local (DEC-038) → Agregar información (operación propuesta, DEC-039) → ficha refrescada → Tarjeta →
// Marcar conversado (3 toques) → Inicio con el nombre → Avance → Asistente (+ Familia nueva). Guarda
// tres capturas PNG (inicio, ficha, agregar información) en SCREENSHOT_DIR (por defecto
// .agents/tasks/frontend-pwa/screenshots) y corre axe en Inicio y Ficha (0 violaciones
// critical/serious). El nombre inventado nunca aparece en
// la consola ni en URLs de requests. Sin llamadas de red reales: el mock vive en la página.
/// <reference lib="dom" />
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MOCK_COPY } from '../src/i18n/es.mock.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = process.env.SCREENSHOT_DIR ?? path.resolve(here, '../../.agents/tasks/frontend-pwa/screenshots');
// El build e2e usa el copy canónico de Rol 4 si existe (misma resolución que vite.config.ts);
// si no, el mock. La prueba lee la misma fuente para no depender de la rama.
const CANONICAL_I18N = path.resolve(here, '..', process.env.BRUJULA_CONTENT_DIR ?? '../content', 'i18n', 'es.json');
const C: typeof MOCK_COPY = existsSync(CANONICAL_I18N)
  ? { ...MOCK_COPY, ...(JSON.parse(readFileSync(CANONICAL_I18N, 'utf8')) as Partial<typeof MOCK_COPY>) }
  : MOCK_COPY;
const NAME = 'Sofía Ficticia';
const generic = (shortId: string) => C['family.generic_name'].replace('{short_id}', shortId);
const leaksName = (text: string) => /sof[ií]a|ficticia|sof%c3%ada/i.test(text);

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

/** href de cada tarjeta de familia en el orden en que se muestran. */
async function familyOrder(page: Page): Promise<string[]> {
  return page.locator('[data-family-row]').evaluateAll((links) => links.map((a) => a.getAttribute('href') ?? ''));
}

test('recorrido principal a 360 px', async ({ page }) => {
  const cspErrors: string[] = [];
  const consoleTexts: string[] = [];
  const requestUrls: string[] = [];
  page.on('console', (message) => {
    consoleTexts.push(message.text());
    if (message.text().includes('Content Security Policy')) cspErrors.push(message.type());
  });
  page.on('request', (request) => requestUrls.push(request.url()));
  page.on('dialog', (dialog) => void dialog.dismiss());

  // Inicio: orden neutro (por family_id, no por prioridad) y acciones prioritarias por familia
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: C['home.title'] })).toBeVisible();
  await expect(page.getByText(C['home.progress'].replace('{informed}', '2').replace('{total}', '8'))).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: C['home.list_title'] })).toBeVisible();
  await expect(page.getByText('Familias por prioridad')).toHaveCount(0);
  await expect(page.getByText(C['home.next_family'])).toHaveCount(0);
  const ids = ['00001', '00002', '00003', '00004', '00005', '00006', '00007', '00008'];
  expect(await familyOrder(page)).toEqual(ids.map((id) => `/familias/FAM-SIM-E3-${id}`));
  await expect(page.getByText(C['home.priority_actions']).first()).toBeVisible();
  await expectAxeClean(page);
  await shot(page, 'c01-inicio');

  // Ficha: acciones prioritarias arriba y todos los beneficios en dos grupos
  await page.locator('[data-family-row]', { hasText: generic('00002') }).click();
  await expect(page.getByRole('heading', { level: 1, name: generic('00002') })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: C['family.top_title'] })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: C['family.applies_title'] })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: C['family.missing_title'] })).toBeVisible();
  await expect(page.locator('[data-benefit-group="missing"] h3')).toHaveCount(2);
  await expectAxeClean(page);
  await shot(page, 'c02-ficha');

  // Nombre de trato (solo en este equipo)
  await page.getByRole('button', { name: C['family.name.open'] }).click();
  await page.getByLabel(C['family.name.title']).fill(NAME);
  await expectNoHorizontalScroll(page);
  await page.getByRole('button', { name: C['family.name.save'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: NAME })).toBeVisible();
  expect(leaksName(await page.title())).toBe(false);
  expect(leaksName(page.url())).toBe(false);

  // Agregar información (operación propuesta, mock) → ficha refrescada
  await page.getByRole('link', { name: C['family.actions.add_info'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['add_info.title'] })).toBeVisible();
  await page.getByRole('group', { name: C['new_family.q.has_rsh'] }).locator('label', { hasText: C['common.yes'] }).click();
  await page.getByRole('group', { name: C['new_family.q.household_income_band'] }).locator('label', { hasText: C['income_band.under_110k'] }).click();
  await shot(page, 'c03-agregar-informacion');
  await page.getByRole('button', { name: C['add_info.submit'] }).click();
  await expect(page.getByText(C['family.add_info_done'])).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: NAME })).toBeVisible();
  await expect(page.locator('[data-benefit-group="missing"] h3')).toHaveCount(0);
  await expect(page.locator('[data-benefit-group="applies"] h3')).toHaveCount(3);
  await expectNoHorizontalScroll(page);

  // Tarjeta (mensaje + CARD_V1)
  await page.getByRole('link', { name: C['family.actions.message'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['message.title'] })).toBeVisible();
  await expect(page.locator('[data-print-root]')).toBeVisible();
  await expect(page.locator('[data-print-root]')).not.toContainText(NAME);
  await expectNoHorizontalScroll(page);
  await page.getByRole('link', { name: C['nav.back'], exact: true }).click();

  // Marcar conversado en exactamente 3 toques
  await page.getByRole('link', { name: C['family.actions.mark'] }).click(); // toque 1
  await expect(page.getByRole('heading', { level: 1, name: C['conversation.title'] })).toBeVisible();
  await expect(page.getByRole('button', { name: C['conversation.confirm'] })).toBeDisabled();
  await page.locator('label', { hasText: C['next_step.go_to_institution'] }).click(); // toque 2
  await page.getByRole('button', { name: C['conversation.confirm'] }).click(); // toque 3
  await expect(page.getByText(C['conversation.success'])).toBeVisible();
  await expectNoHorizontalScroll(page);

  // Inicio: la familia con nombre va primero (alfabético); el resto sigue por family_id
  await page.getByRole('link', { name: C['nav.home'], exact: true }).click();
  await expect(page.locator('[data-family-row]').first()).toContainText(NAME);
  expect(await familyOrder(page)).toEqual(['00002', '00001', '00003', '00004', '00005', '00006', '00007', '00008'].map((id) => `/familias/FAM-SIM-E3-${id}`));
  await expectNoHorizontalScroll(page);

  // Avance: sube SOLO con el dato del servidor (2 → 3 de 8 en el jardín)
  await page.getByRole('link', { name: C['nav.kpi'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['kpi.title'] })).toBeVisible();
  await expect(page.getByText(C['kpi.ratio'].replace('{informed}', '3').replace('{total}', '8'))).toBeVisible();
  await expect(page.locator('[data-primary-action]')).toHaveCount(0);

  // Asistente: pregunta de ejemplo → respuesta CATALOG_INFO con citas
  await page.getByRole('link', { name: C['nav.assistant'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['assistant.title'] })).toBeVisible();
  await page.getByRole('button', { name: C['assistant.example.1'] }).click();
  await page.getByRole('button', { name: C['assistant.submit'], exact: true }).click();
  await expect(page.getByRole('heading', { name: C['assistant.answer_title'] })).toBeVisible();
  await expect(page.getByRole('link', { name: /SRC-SIM-001/ })).toHaveAttribute('href', /^https:\/\//);

  // Familia nueva (paso 1)
  await page.getByRole('link', { name: C['nav.new_family'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['new_family.title'] })).toBeVisible();

  expect(cspErrors).toEqual([]);
  // El nombre de trato nunca sale a la consola ni a una URL de request.
  expect(consoleTexts.filter(leaksName)).toEqual([]);
  expect(requestUrls.filter(leaksName)).toEqual([]);
});
