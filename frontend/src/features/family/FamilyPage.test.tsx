// Ficha familia con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { t } from '../../i18n/copy';
import { fichaBrecha, payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import FamilyPage from './FamilyPage';

function renderFamily(familyId = 'FAM-SIM-E3-00001') {
  return renderWithProviders(
    <Routes>
      <Route path="/familias/:familyId" element={<FamilyPage />} />
    </Routes>,
    { route: `/familias/${familyId}` },
  );
}

describe('FamilyPage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => resetTestRuntime());

  it('muestra el top tres en el orden de C3 con chips, “por qué”, aviso y fuentes HTTPS', async () => {
    const user = userEvent.setup();
    renderFamily();
    const top = fichaBrecha().data.top_opportunities;
    await screen.findByRole('heading', { level: 3, name: top[0]?.simple_title });

    const cards = screen.getAllByRole('article');
    // Orden de C3 respetado aunque la posición 1 tenga la urgencia más baja (U 0,45).
    expect(cards.map((card) => within(card).getByRole('heading', { level: 3 }).textContent)).toEqual(top.map((o) => o.simple_title));
    const first = cards[0] as HTMLElement;
    expect(within(first).getByText(t('card.why_first_label'))).toBeVisible();
    expect(within(first).getByText(top[0]?.why_first ?? '')).toBeVisible();
    expect(within(first).getByText(t('group.go.label'))).toBeInTheDocument();
    expect(within(cards[1] as HTMLElement).getByText(t('chip.urgency.high'))).toBeInTheDocument();
    expect(screen.getByText(t('notice.referential'))).toBeInTheDocument();

    await user.click(within(first).getByRole('button', { name: t('card.expand') }));
    const source = within(first).getByRole('link', { name: new RegExp(t('card.source_link', { source_id: 'SRC-SIM-001' })) });
    expect(source).toHaveAttribute('href', top[0]?.sources[0]?.url);
    expect(source).toHaveAttribute('rel', 'noopener noreferrer external');

    // Códigos técnicos solo dentro de [data-technical].
    const main = document.body.cloneNode(true) as HTMLElement;
    main.querySelectorAll('[data-technical]').forEach((node) => node.remove());
    expect(main.textContent).not.toMatch(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/);
    expect(screen.getByRole('link', { name: t('family.actions.mark') })).toHaveAttribute('href', '/familias/FAM-SIM-E3-00001/conversacion');
  });

  it('404 al cargar la ficha → mensaje seguro sin el texto del servidor', async () => {
    server.use(overrideOperation('getFamilia', () => HttpResponse.json(payloadOf('error.404'), { status: 404 })));
    renderFamily();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.not_found'))).toBeInTheDocument();
    expect(alert.textContent).not.toContain('Recurso inexistente');
  });
});
