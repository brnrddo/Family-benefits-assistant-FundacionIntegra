// Inicio con el mock-servidor C3 (setupServer). Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { t } from '../../i18n/copy';
import { familiasPage1, jardines } from '../../test/fixtures';
import { mockServer } from '../../test/mswServer';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
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
  afterEach(() => resetTestRuntime());

  it('muestra el avance y las familias en el orden de C3, con semáforo y la siguiente familia', async () => {
    renderHome();
    const page = familiasPage1().items;
    const last = page[page.length - 1];
    await screen.findByText(t('home.family_item', { family_id: last?.family_id ?? '' }));
    const section = screen.getByRole('heading', { name: t('home.list_title') }).closest('section');
    expect(section).not.toBeNull();
    const hrefs = within(section as HTMLElement)
      .getAllByRole('link')
      .map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(page.map((f) => `/familias/${f.family_id}`));

    const garden = jardines().items[0];
    expect(garden).toBeDefined();
    expect(screen.getByText(t('home.progress', { informed: String(garden?.families_informed), total: String(garden?.families_total) }))).toBeInTheDocument();
    expect(screen.getAllByText(t('traffic_light.verde')).length).toBeGreaterThan(0);

    const next = screen.getByRole('link', { name: t('home.family_item', { family_id: 'FAM-SIM-E3-00001' }) });
    expect(next).toHaveAttribute('data-primary-action');
    expect(next).toHaveAttribute('href', '/familias/FAM-SIM-E3-00001');
  });

  it('error 503 en la lista de familias → mensaje seguro con Reintentar', async () => {
    mockServer.setScenario('error503');
    renderHome();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.unavailable'))).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: t('common.retry') })).toBeInTheDocument();
  });
});
