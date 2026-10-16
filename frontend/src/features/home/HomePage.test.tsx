// Inicio con el mock-servidor C3 (setupServer). Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { FamiliaListEnvelope } from '../../api/types';
import { sortFamiliesNeutral } from '../../domain/familyOrder';
import { benefitLabel, t } from '../../i18n/copy';
import { familiasPage1, familiasPage2, jardines } from '../../test/fixtures';
import { mockServer, server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import { clearDemoData } from '../../offline/db';
import { clearLocalNamesMemory, refreshLocalNames } from '../../offline/localNames';
import { seedLocalNames } from '../../offline/localNamesSeed';
import { clearDoneActionsMemory } from '../../offline/doneActions';
import { QUICK_INFORM_COPY } from '../conversation/QuickInform';
import { DEMO_COPY, listOpen } from '../demo-session/demoCopy';
import HomePage from './HomePage';

function renderHome() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>,
    { route: '/' },
  );
}

describe('HomePage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => {
    clearDoneActionsMemory();
    resetTestRuntime();
  });

  it('DEC-091: "Ya le informé" en la tarjeta Hoy pasa a la siguiente familia y deja el ✓ de memoria', async () => {
    const user = userEvent.setup();
    renderHome();
    const today = (await screen.findByRole('heading', { level: 2, name: DEMO_COPY.todayTitle })).closest('section') as HTMLElement;
    // Mayor priority_score sin conversar: FAM-SIM-E3-00001, primer apoyo BEN-001.
    expect(within(today).getByText(/la familia 00001/)).toHaveTextContent(benefitLabel('BEN-001'));
    expect(today.querySelector('[data-done-line]')).toBeNull();

    await user.click(within(today).getByRole('button', { name: QUICK_INFORM_COPY.button }));

    // Siguiente según el motor: FAM-SIM-E3-00002 (BEN-003); la memoria recuerda la anterior.
    expect(await within(today).findByText(/la familia 00002/)).toHaveTextContent(benefitLabel('BEN-003'));
    expect(within(today).getByText('Ya habló con la familia 00001 ✓ (hoy)')).toBeInTheDocument();
  });

  it('DEC-037: orden neutro por nombre/family_id que NO depende de priority_score, con acciones prioritarias', async () => {
    // Las 8 familias del jardín en orden inverso y con puntajes invertidos: el orden mostrado no cambia.
    const items = [...familiasPage1().items, ...familiasPage2().items];
    const scores = items.map((f) => f.priority_score).reverse();
    const shuffled: FamiliaListEnvelope = {
      ...familiasPage1(),
      items: [...items].reverse().map((f, i) => ({ ...f, priority_score: scores[i] ?? 0 })),
      next_cursor: null,
    };
    server.use(overrideOperation('listFamiliasByJardin', () => HttpResponse.json(shuffled)));
    renderHome();
    const user = userEvent.setup();
    const section = (await screen.findByRole('heading', { name: t('home.list_title') })).closest('section') as HTMLElement;
    // Lista y resumen vienen plegados (DEC-091).
    await user.click(within(section).getByRole('button', { name: listOpen(items.length) }));
    await user.click(screen.getByRole('button', { name: DEMO_COPY.statsOpen }));
    const hrefs = within(section)
      .getAllByRole('link')
      .map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(items.map((f) => `/familias/${f.family_id}`).sort());
    expect(screen.queryByText(t('home.next_family'))).toBeNull();

    // Tarjeta: genérico + ID corto, acciones prioritarias (top_benefit_ids), semáforo y total.
    const card = within(section).getByRole('link', { name: new RegExp(t('family.generic_name', { short_id: '00002' })) });
    expect(within(card).getByText(t('home.priority_actions'))).toBeInTheDocument();
    for (const id of ['BEN-003', 'BEN-005', 'BEN-006']) expect(within(card).getByText(benefitLabel(id))).toBeInTheDocument();
    expect(within(card).getByText(t('traffic_light.amarillo'))).toBeInTheDocument();
    const garden = jardines().items[0];
    expect(screen.getByText(t('home.progress', { informed: String(garden?.families_informed), total: String(garden?.families_total) }))).toBeInTheDocument();

    // Con nombre de trato, esa familia va primero (alfabético); el resto por family_id.
    const named = sortFamiliesNeutral(items, new Map([['FAM-SIM-E3-00007', 'Ámbar Ficticia']]));
    expect(named.map((f) => f.family_id).slice(0, 2)).toEqual(['FAM-SIM-E3-00007', 'FAM-SIM-E3-00001']);
  });

  it('buscar un nombre de trato deja una sola familia en la lista (local, sin red)', async () => {
    resetTestRuntime();
    installTestRuntime({ persistence: true });
    await clearDemoData();
    await seedLocalNames();
    await refreshLocalNames();
    try {
      renderHome();
      const search = await screen.findByRole('searchbox', { name: DEMO_COPY.searchLabel });
      expect(document.querySelectorAll('[data-family-row]').length).toBeGreaterThan(1);
      await userEvent.setup().type(search, 'benjamin');
      const rows = document.querySelectorAll('[data-family-row]');
      expect(rows).toHaveLength(1);
      expect(rows[0]).toHaveTextContent('Benjamín T.');
    } finally {
      clearLocalNamesMemory();
      await clearDemoData();
    }
  });
  it('error 503 en la lista de familias → mensaje seguro con Reintentar', async () => {
    mockServer.setScenario('error503');
    renderHome();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.unavailable'))).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: t('common.retry') })).toBeInTheDocument();
  });
});
