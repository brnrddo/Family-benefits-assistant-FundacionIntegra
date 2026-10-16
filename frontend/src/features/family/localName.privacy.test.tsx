// Privacidad del nombre de trato (DEC-038; PRIVACIDAD_DEMO.md, clase "Local de la tía"). Recorre la
// app completa (router real + AppShell) con el mock-servidor y CAPTURA cada request en el `fetch` del
// transporte: el nombre nunca aparece en URL, headers ni body (conversación, guion, mensaje,
// asistente, la operación propuesta ni ninguna lectura) ni en logs. Guion y mensaje ya no tienen botón
// en la ficha: se abren por URL directa. También: logout borra los
// nombres. DEC-047: lo escrito se guarda como "Nombre I." y los nombres sembrados en Demo cumplen lo
// mismo. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON); los nombres son inventados.
import { QueryClientProvider } from '@tanstack/react-query';
import { act, cleanup, configure, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { performLogout } from '../../auth/logout';
import { getSession } from '../../auth/session';
import { t } from '../../i18n/copy';
import { log } from '../../lib/log';
import { clearDemoData, openDemoDb } from '../../offline/db';
import { clearLocalNamesMemory, currentLocalNames, refreshLocalNames, saveLocalName } from '../../offline/localNames';
import { seedLocalNames } from '../../offline/localNamesSeed';
import { createTestQueryClient } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import { routes } from '../../router';
import { listOpen } from '../demo-session/demoCopy';
import { familyRoutes } from './routes';

// Router real con páginas diferidas (lazy): la primera carga de cada vista tarda más en jsdom.
configure({ asyncUtilTimeout: 8000 });

const NAME = 'Sofía Ficticia';
/** DEC-047: lo que queda guardado es solo el primer nombre + inicial. */
const SAVED = 'Sofía F.';
const FAMILY = 'FAM-SIM-E3-00002';
/**
 * Variantes que no deben salir del equipo: con y sin tilde, cada palabra, cualquier caso. Incluye el
 * apellido completo ('ficticia'): no se guarda ni sale (DEC-047).
 */
const NEEDLES = ['sofía', 'sofia', 'ficticia', 'sof%c3%ada', 'sof\\u00eda'];
/** Nombre sembrado (inventado) de FAMILY en `localNamesSeed.json` (DEC-047). */
const SEEDED = 'Benjamín T.';
const SEEDED_NEEDLES = ['benjamín', 'benjamin', 'benjam%c3%adn', 'benjam\\u00edn'];

interface Captured {
  readonly method: string;
  readonly url: string;
  readonly headers: string;
  readonly body: string;
}

function leaks(text: string, needles: readonly string[] = NEEDLES): boolean {
  const lower = text.toLowerCase();
  return needles.some((needle) => lower.includes(needle));
}

/** Espía `log` y `console`: devuelve todo lo que se intentó registrar. */
function spyLogs(): { readonly logged: unknown[]; readonly consoleCalls: unknown[] } {
  const logged: unknown[] = [];
  vi.spyOn(log, 'warn').mockImplementation((fields) => void logged.push(fields));
  vi.spyOn(log, 'error').mockImplementation((fields) => void logged.push(fields));
  const consoleCalls: unknown[] = [];
  for (const method of ['log', 'info', 'warn', 'error', 'debug'] as const) {
    vi.spyOn(console, method).mockImplementation((...args: unknown[]) => void consoleCalls.push(args));
  }
  return { logged, consoleCalls };
}

describe('nombre de trato: nunca sale del equipo', () => {
  const captured: Captured[] = [];

  beforeEach(async () => {
    captured.length = 0;
    // Mismo transporte fetch de la app, con un `fetch` que registra TODO request antes de enviarlo.
    installTestRuntime({
      persistence: true,
      fetchImpl: async (input, init) => {
        const request = input instanceof Request ? input : new Request(input, init);
        const body = request.method === 'GET' ? '' : await request.clone().text();
        captured.push({ method: request.method, url: request.url, headers: JSON.stringify([...request.headers.entries()]), body });
        return fetch(request);
      },
    });
    await clearDemoData();
    await refreshLocalNames();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    cleanup();
    clearLocalNamesMemory();
    await clearDemoData();
    resetTestRuntime();
  });

  it('flujo completo: Inicio → nombre → Agregar información → guion → mensaje → conversado → asistente', { timeout: 30_000 }, async () => {
    const user = userEvent.setup();
    const { logged, consoleCalls } = spyLogs();

    const router = createMemoryRouter(routes, { initialEntries: ['/'] });
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Inicio → ficha (tarjeta con nombre genérico; la lista viene plegada, DEC-091)
    await user.click(await screen.findByRole('button', { name: listOpen(8) }));
    await user.click(await screen.findByRole('link', { name: new RegExp(t('family.generic_name', { short_id: '00002' })) }));
    await screen.findByRole('heading', { level: 1, name: t('family.generic_name', { short_id: '00002' }) });

    // Nombre de trato (solo en este equipo)
    await user.click(await screen.findByRole('button', { name: t('family.name.open') }));
    await user.type(screen.getByLabelText(t('family.name.title')), NAME);
    await user.click(screen.getByRole('button', { name: t('family.name.save') }));
    await screen.findByRole('heading', { level: 1, name: SAVED });
    // Ni la pestaña ni el historial del navegador (que el logout no borra) llevan el nombre.
    expect(leaks(document.title)).toBe(false);
    expect(leaks(router.state.location.pathname + router.state.location.search)).toBe(false);

    // Agregar información (operación propuesta) → ficha refrescada
    await user.click(await screen.findByRole('link', { name: t('family.actions.add_info') }));
    const rsh = await screen.findByRole('group', { name: t('new_family.q.has_rsh') });
    await user.click(within(rsh).getByRole('radio', { name: t('common.yes') }));
    await user.click(within(screen.getByRole('group', { name: t('new_family.q.household_income_band') })).getByRole('radio', { name: t('income_band.under_110k') }));
    await user.click(screen.getByRole('button', { name: t('add_info.submit') }));
    await screen.findByText(t('family.add_info_done'));
    expect(screen.getByRole('heading', { level: 1, name: SAVED })).toBeInTheDocument();

    // Guion y mensaje (POST de generación), por URL directa
    await act(() => router.navigate(familyRoutes.guion(FAMILY)));
    await screen.findByText(t('script.read_hint'));
    await act(() => router.navigate(familyRoutes.mensaje(FAMILY)));
    await waitFor(() => expect(document.querySelector('[data-print-root]')).not.toBeNull());
    await user.click(screen.getByRole('link', { name: t('nav.back') }));

    // Marcar conversado (3 toques)
    await user.click(await screen.findByRole('link', { name: t('family.actions.mark') }));
    await user.click(await screen.findByRole('radio', { name: t('next_step.go_to_institution') }));
    await user.click(screen.getByRole('button', { name: t('conversation.confirm') }));
    await screen.findByText(t('conversation.success'));
    expect(screen.getByText(SAVED)).toBeInTheDocument();

    // Asistente: una pregunta con el nombre SÍ se envía, con el nombre reemplazado (el body se revisa
    // abajo: el nombre nunca sale); una general también.
    await user.click(screen.getByRole('link', { name: t('nav.assistant') }));
    const field = await screen.findByLabelText(new RegExp(t('assistant.question_label')));
    await user.type(field, '¿Qué apoyos hay para sofia?');
    const before = captured.length;
    await user.click(screen.getByRole('button', { name: t('assistant.submit') }));
    await screen.findByRole('heading', { name: t('assistant.answer_title') });
    expect(captured.length).toBeGreaterThan(before);
    expect(screen.queryByText(t('assistant.name_blocked'))).toBeNull();
    await user.clear(field);
    await user.type(field, '¿Qué es el Registro Social de Hogares?');
    await user.click(screen.getByRole('button', { name: t('assistant.submit') }));
    await waitFor(() => expect(screen.getAllByRole('heading', { name: t('assistant.answer_title') })).toHaveLength(2));

    // El diálogo de logout avisa que se borrarán los nombres (sin confirmar aquí).
    await user.click(screen.getByRole('button', { name: t('auth.logout') }));
    expect(screen.getByText(t('auth.logout_confirm.body_names', { count: '1' }))).toBeInTheDocument();

    // --- Ningún request lleva el nombre (URL, headers, body) ---
    const routesSeen = captured.map((c) => `${c.method} ${new URL(c.url).pathname}`);
    for (const expected of [
      `GET /api/v1/familias/${FAMILY}`,
      `POST /api/v1/familias/${FAMILY}/antecedentes`,
      `POST /api/v1/familias/${FAMILY}/guion`,
      `POST /api/v1/familias/${FAMILY}/mensaje`,
      `POST /api/v1/familias/${FAMILY}/conversaciones`,
      'POST /api/v1/asistente',
    ]) {
      expect(routesSeen).toContain(expected);
    }
    for (const request of captured) {
      expect(leaks(request.url), request.url).toBe(false);
      expect(leaks(request.headers), `${request.method} ${request.url} headers`).toBe(false);
      expect(leaks(request.body), `${request.method} ${request.url} body`).toBe(false);
    }
    // --- Ni en logs ni en consola ---
    expect(leaks(JSON.stringify(logged))).toBe(false);
    expect(leaks(JSON.stringify(consoleCalls))).toBe(false);
    // Sí quedó guardado (solo nombre + inicial), pero solo en este equipo.
    expect(currentLocalNames().get(FAMILY)).toBe(SAVED);
  });

  it('nombre sembrado (DEC-047): ficha, guion, mensaje, asistente y logout sin que salga del equipo', { timeout: 30_000 }, async () => {
    expect(await seedLocalNames()).toBe(9);
    await refreshLocalNames();
    const user = userEvent.setup();
    const { logged, consoleCalls } = spyLogs();
    const seededLeaks = (text: string) => leaks(text, SEEDED_NEEDLES);

    const router = createMemoryRouter(routes, { initialEntries: [`/familias/${FAMILY}`] });
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await screen.findByRole('heading', { level: 1, name: SEEDED });
    expect(seededLeaks(document.title)).toBe(false);
    expect(seededLeaks(router.state.location.pathname + router.state.location.search)).toBe(false);

    // Guion y mensaje (POST de generación) por URL directa; la tarjeta imprimible no lleva el nombre.
    await act(() => router.navigate(familyRoutes.guion(FAMILY)));
    await screen.findByText(t('script.read_hint'));
    await act(() => router.navigate(familyRoutes.mensaje(FAMILY)));
    await waitFor(() => expect(document.querySelector('[data-print-root]')).not.toBeNull());
    expect(seededLeaks(document.querySelector('[data-print-root]')?.textContent ?? '')).toBe(false);
    await user.click(screen.getByRole('link', { name: t('nav.back') }));
    await screen.findByRole('heading', { level: 1, name: SEEDED });

    // Asistente: el primer nombre solo (sin tilde) se reemplaza y la pregunta se envía; el body se
    // revisa abajo: el nombre nunca sale.
    await user.click(screen.getByRole('link', { name: t('nav.assistant') }));
    const field = await screen.findByLabelText(new RegExp(t('assistant.question_label')));
    await user.type(field, '¿Qué apoyos hay para benjamin?');
    const before = captured.length;
    await user.click(screen.getByRole('button', { name: t('assistant.submit') }));
    await screen.findByRole('heading', { name: t('assistant.answer_title') });
    expect(captured.length).toBeGreaterThan(before);

    // El aviso de logout cuenta también los sembrados (sin confirmar aquí).
    await user.click(screen.getByRole('button', { name: t('auth.logout') }));
    expect(screen.getByText(t('auth.logout_confirm.body_names', { count: '9' }))).toBeInTheDocument();

    const routesSeen = captured.map((c) => `${c.method} ${new URL(c.url).pathname}`);
    for (const expected of [`GET /api/v1/familias/${FAMILY}`, `POST /api/v1/familias/${FAMILY}/guion`, `POST /api/v1/familias/${FAMILY}/mensaje`]) {
      expect(routesSeen).toContain(expected);
    }
    for (const request of captured) {
      expect(seededLeaks(request.url), request.url).toBe(false);
      expect(seededLeaks(request.headers), `${request.method} ${request.url} headers`).toBe(false);
      expect(seededLeaks(request.body), `${request.method} ${request.url} body`).toBe(false);
    }
    expect(seededLeaks(JSON.stringify(logged))).toBe(false);
    expect(seededLeaks(JSON.stringify(consoleCalls))).toBe(false);

    // Logout borra también los sembrados.
    await performLogout(createTestQueryClient(), vi.fn());
    expect(currentLocalNames().size).toBe(0);
  });

  it('logout borra los nombres del equipo (IndexedDB y memoria)', async () => {
    expect((await saveLocalName(FAMILY, NAME)).ok).toBe(true);
    const db = await openDemoDb();
    expect(await db.get('names', FAMILY)).toMatchObject({ family_id: FAMILY, name: SAVED });

    const navigate = vi.fn();
    await performLogout(createTestQueryClient(), navigate);

    expect(navigate).toHaveBeenCalledWith('/');
    expect(currentLocalNames().size).toBe(0);
    await refreshLocalNames();
    expect(currentLocalNames().size).toBe(0);
    const reopened = await openDemoDb();
    expect(await reopened.getAll('names')).toEqual([]);
    expect(getSession().authMode).toBe('none');
  });
});
