// Smoke e2e a 360 px con mocks C3 sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON), recorrido de la demo:
// Inicio (estadísticas del jardín + acceso al chat + búsqueda + lista con nombres de trato sembrados,
// DEC-047) → buscar un nombre deja una fila → Ficha (secciones y filtro; "Datos del hogar" plegada)
// → nombre de trato local (DEC-038) → Agregar información (operación propuesta, DEC-039) → Marcar conversado (3 toques) →
// Inicio → Preguntar → chip de situación → respuesta con fuentes. Guarda capturas PNG en
// SCREENSHOT_DIR (por defecto .agents/tasks/frontend-pwa/screenshots), también a escritorio, y corre
// axe en Inicio, Ficha y Preguntar (0 violaciones critical/serious). El nombre inventado nunca aparece
// en la consola ni en URLs de requests. Sin llamadas de red reales: el mock vive en la página.
/// <reference lib="dom" />
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ADD_INFO_COPY } from '../src/api/proposals/addInfoCopy.ts';
import { DEMO_COPY, SITUATION_EXAMPLES } from '../src/features/demo-session/demoCopy.ts';
import { FAMILY_COPY } from '../src/features/family/familyCopy.ts';
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
/** DEC-047: se guarda solo "PrimerNombre I.". */
const NAME_SHORT = 'Sofía F.';
const SEEDED = 'Benjamín T.'; // FAM-SIM-E3-00002 en la semilla de mocks
const leaksName = (text: string) => /sof[ií]a|ficticia|sof%c3%ada/i.test(text);
const SITUATION = SITUATION_EXAMPLES[0] ?? '';

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
 * agranda la ventana al alto del documento y luego se restaura el ancho pedido × 800.
 */
async function shot(page: Page, name: string, width = 360): Promise<void> {
  if (width === 360) await expectNoHorizontalScroll(page);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width, height: Math.max(800, height) });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`) });
  await page.setViewportSize({ width: 360, height: 800 });
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

  // Inicio: estadísticas del jardín, acceso al chat, búsqueda y familias con nombre de trato
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: C['home.title'] })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: DEMO_COPY.statsTitle })).toBeVisible();
  await expect(page.getByText(C['home.progress'].replace('{informed}', '2').replace('{total}', '8'))).toBeVisible();
  await expect(page.getByRole('heading', { level: 3, name: DEMO_COPY.statsTopTitle })).toBeVisible();
  await expect(page.getByRole('link', { name: DEMO_COPY.homeChatCta })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: C['home.list_title'] })).toBeVisible();
  await expect(page.locator('[data-family-row]')).toHaveCount(8);
  // Sin "Familia 00xxx": todas las familias de los mocks tienen nombre sembrado.
  await expect(page.getByText(C['family.generic_name'].replace('{short_id}', '00002'))).toHaveCount(0);
  await expectAxeClean(page);
  await shot(page, 'c01-inicio');
  await shot(page, 'c01-inicio-escritorio', 1280);

  // Búsqueda local por nombre → una fila
  await page.getByRole('searchbox', { name: DEMO_COPY.searchLabel }).fill('benjamin');
  await expect(page.locator('[data-family-row]')).toHaveCount(1);
  await expect(page.locator('[data-family-row]')).toContainText(SEEDED);
  await shot(page, 'c02-busqueda');

  // Ficha: beneficios por sección ("Puede postular ahora", "Falta información") con filtro
  await page.locator('[data-family-row]', { hasText: SEEDED }).click();
  await expect(page.getByRole('heading', { level: 1, name: SEEDED })).toBeVisible();
  await expect(page.getByRole('radio', { name: FAMILY_COPY.filterAll })).toBeChecked();
  await expect(page.getByRole('heading', { level: 2, name: FAMILY_COPY.sectionApply })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: FAMILY_COPY.sectionMissing })).toBeVisible();
  await expect(page.locator('[data-benefit-section="missing"] [data-benefit-card]')).toHaveCount(2);
  await expectAxeClean(page);
  await shot(page, 'c03-ficha');

  // Nombre de trato (solo en este equipo)
  await page.getByRole('button', { name: C['family.name.change'] }).click();
  await page.getByLabel(C['family.name.title']).fill(NAME);
  await expectNoHorizontalScroll(page);
  await page.getByRole('button', { name: C['family.name.save'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: NAME_SHORT })).toBeVisible();
  expect(leaksName(await page.title())).toBe(false);
  expect(leaksName(page.url())).toBe(false);

  // Agregar información (operación propuesta, mock) → ficha refrescada
  await page.getByRole('button', { name: ADD_INFO_COPY.householdTitle }).click();
  await page.locator('[data-household]').getByRole('link', { name: C['family.actions.add_info'] }).click();
  await expect(page.getByRole('heading', { level: 1, name: C['add_info.title'] })).toBeVisible();
  await page.getByRole('group', { name: C['new_family.q.has_rsh'] }).locator('label', { hasText: C['common.yes'] }).click();
  await page.getByRole('group', { name: C['new_family.q.household_income_band'] }).locator('label', { hasText: C['income_band.under_110k'] }).click();
  await page.getByRole('button', { name: C['add_info.submit'] }).click();
  await expect(page.getByText(C['family.add_info_done'])).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: NAME_SHORT })).toBeVisible();
  await expect(page.locator('[data-benefit-section="missing"]')).toHaveCount(0);
  await expect(page.locator('[data-benefit-section="apply"] [data-benefit-card]')).toHaveCount(3);
  await expectNoHorizontalScroll(page);

  // Marcar conversado en exactamente 3 toques
  await page.getByRole('link', { name: C['family.actions.mark'] }).click(); // toque 1
  await expect(page.getByRole('heading', { level: 1, name: C['conversation.title'] })).toBeVisible();
  await expect(page.getByRole('button', { name: C['conversation.confirm'] })).toBeDisabled();
  await page.locator('label', { hasText: C['next_step.go_to_institution'] }).click(); // toque 2
  await page.getByRole('button', { name: C['conversation.confirm'] }).click(); // toque 3
  await expect(page.getByText(C['conversation.success'])).toBeVisible();
  await expectNoHorizontalScroll(page);

  // Inicio: la familia ahora lleva el nombre que puso la tía
  await page.getByRole('link', { name: C['nav.home'], exact: true }).click();
  await expect(page.locator('[data-family-row]', { hasText: NAME_SHORT })).toHaveCount(1);
  await expectNoHorizontalScroll(page);

  // Preguntar: chip de situación → respuesta CATALOG_INFO con fuentes
  await page.getByRole('link', { name: C['nav.assistant'], exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: DEMO_COPY.chatTitle })).toBeVisible();
  await page.getByRole('button', { name: SITUATION }).click();
  await expect(page.getByRole('link', { name: /SRC-SIM-001/ })).toHaveAttribute('href', /^https:\/\//);
  await expect(page.getByText(C['notice.referential']).first()).toBeVisible();
  // Pregunta del jardín: respuesta local desde /kpi, sin /asistente
  await page.getByRole('button', { name: 'Tengo reunión de apoderados el jueves' }).click();
  await expect(page.getByText(/Para la reunión, el tema con más familias/)).toBeVisible();
  await expectAxeClean(page);
  await shot(page, 'c04-asistente');
  await shot(page, 'c04-asistente-escritorio', 1280);

  expect(cspErrors).toEqual([]);
  // El nombre de trato nunca sale a la consola ni a una URL de request.
  expect(consoleTexts.filter(leaksName)).toEqual([]);
  expect(requestUrls.filter(leaksName)).toEqual([]);
});
