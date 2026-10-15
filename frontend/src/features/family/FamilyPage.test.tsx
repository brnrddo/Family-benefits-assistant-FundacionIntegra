// Ficha familia con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { OpportunityListEnvelope } from '../../api/types';
import { configureRuntime, resolveProfile } from '../../config/profile';
import { benefitName, t } from '../../i18n/copy';
import { clearDemoData } from '../../offline/db';
import { clearLocalNamesMemory, currentLocalNames } from '../../offline/localNames';
import { fichaBrecha, payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import AddInfoPage from '../add-info/AddInfoPage';
import FamilyPage from './FamilyPage';

function renderFamily(familyId = 'FAM-SIM-E3-00001') {
  return renderWithProviders(
    <Routes>
      <Route path="/familias/:familyId" element={<FamilyPage />} />
      <Route path="/familias/:familyId/agregar-informacion" element={<AddInfoPage />} />
    </Routes>,
    { route: `/familias/${familyId}` },
  );
}

describe('FamilyPage', () => {
  beforeEach(() => installTestRuntime({ persistence: true }));
  afterEach(async () => {
    cleanup();
    clearLocalNamesMemory();
    await clearDemoData();
    resetTestRuntime();
  });

  it('muestra las acciones prioritarias en el orden de C3 con chips, “por qué”, aviso y fuentes HTTPS', async () => {
    const user = userEvent.setup();
    renderFamily();
    const top = fichaBrecha().data.top_opportunities;
    await screen.findAllByRole('article');

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

  it('todos los beneficios en dos grupos, tal como vienen de C3 (sin NO/NO_APLICA)', async () => {
    renderFamily();
    const applies = (await screen.findByRole('heading', { name: t('family.applies_title') })).closest('section') as HTMLElement;
    const missing = screen.getByRole('heading', { name: t('family.missing_title') }).closest('section') as HTMLElement;
    const titles = (root: HTMLElement) => within(root).getAllByRole('heading', { level: 3 }).map((h) => h.textContent);
    const ficha = fichaBrecha().data;
    const prioridad = payloadOf<OpportunityListEnvelope>('listOportunidades.FAM-SIM-E3-00001.prioridad').items;
    const title = (id: string) => benefitName(id, [...prioridad, ...ficha.top_opportunities].find((o) => o.benefit_id === id)?.simple_title);
    // BEN-001/002/004 son SI; BEN-003 INDETERMINADO; BEN-010 NO no se muestra.
    await waitFor(() => expect(titles(applies)).toEqual([title('BEN-001'), title('BEN-002'), title('BEN-004')]));
    expect(titles(missing)).toEqual([title('BEN-003')]);
    expect(within(applies).getAllByText(t('level.confirmado'))).toHaveLength(2);
    expect(within(missing).getByText(t('context.missing.last_health_control_date'))).toBeInTheDocument();
    const question = ficha.top_opportunities.find((o) => o.benefit_id === 'BEN-003')?.suggested_questions[0] ?? '';
    expect(within(missing).getByText(question)).toBeInTheDocument();
  });

  it('DEC-038: el nombre de trato se guarda solo en este equipo y reemplaza el título genérico', async () => {
    const user = userEvent.setup();
    renderFamily('FAM-SIM-E3-00002');
    expect(await screen.findByRole('heading', { level: 1, name: t('family.generic_name', { short_id: '00002' }) })).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: t('family.name.open') }));
    await user.type(screen.getByLabelText(t('family.name.title')), '  Sofía   Ficticia ');
    await user.click(screen.getByRole('button', { name: t('family.name.save') }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Sofía Ficticia' })).toBeInTheDocument();
    expect(currentLocalNames().get('FAM-SIM-E3-00002')).toBe('Sofía Ficticia');
    expect(screen.getByRole('link', { name: t('family.actions.add_info') })).toHaveAttribute('href', '/familias/FAM-SIM-E3-00002/agregar-informacion');
  });

  it('404 al cargar la ficha → mensaje seguro sin el texto del servidor', async () => {
    server.use(overrideOperation('getFamilia', () => HttpResponse.json(payloadOf('error.404'), { status: 404 })));
    renderFamily();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.not_found'))).toBeInTheDocument();
    expect(alert.textContent).not.toContain('Recurso inexistente');
  });
});

describe('FamilyPage en perfil escala (DEC-038, DEC-039)', () => {
  beforeEach(() => {
    installTestRuntime();
    const escala = resolveProfile(
      {
        VITE_PROFILE: 'escala',
        VITE_API_BASE_URL: 'https://api.brujula-demo.example/api/v1',
        VITE_AUTH_MODE: 'cognito',
        VITE_COGNITO_AUTHORITY: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_SIMPOOL01',
        VITE_COGNITO_DOMAIN: 'https://auth.brujula-demo.example',
        VITE_COGNITO_CLIENT_ID: 'simclientid0001',
        VITE_COGNITO_SCOPES: 'openid familias:read',
        // Aunque alguien active la propuesta, en escala sigue oculta.
        VITE_PROPOSAL_ADD_INFO: 'true',
      },
      { isSecureContext: true },
    );
    if (!escala.ok) throw new Error('escala_config');
    configureRuntime(escala.config);
  });
  afterEach(() => {
    cleanup();
    resetTestRuntime();
  });

  it('no muestra el editor de nombre ni el botón Agregar información', async () => {
    renderFamily('FAM-SIM-E3-00002');
    await screen.findByRole('heading', { name: t('family.applies_title') });
    expect(document.querySelector('[data-name-editor]')).toBeNull();
    expect(screen.queryByLabelText(t('family.name.title'))).toBeNull();
    expect(screen.queryByRole('link', { name: t('family.actions.add_info') })).toBeNull();
    expect(screen.getByRole('link', { name: t('family.actions.mark') })).toBeInTheDocument();
  });
});
