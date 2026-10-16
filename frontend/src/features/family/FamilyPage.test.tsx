// Ficha familia con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { OpportunityListEnvelope } from '../../api/types';
import { configureRuntime, resolveProfile } from '../../config/profile';
import { ACCESS_STATE_KEY, LEVEL_KEY } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { clearDemoData } from '../../offline/db';
import { clearLocalNamesMemory, currentLocalNames } from '../../offline/localNames';
import { fichaBrecha, payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import AddInfoPage from '../add-info/AddInfoPage';
import { FAMILY_COPY } from './familyCopy';
import FamilyPage from './FamilyPage';

// DEC-072: texto provisional del módulo de propuesta (literal: es lo que ve la tía).
const DEMO_TITLE = 'Programa Municipal Sintético de Apoyo Familiar (solo demo)';
const LOCAL_CHIP = 'Disponible en su comuna';
const DEMO_LABEL = 'Solo demo';

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

  it('secciones en el orden de C3, filtro con conteos y tarjetas solo con el nombre', async () => {
    const user = userEvent.setup();
    renderFamily();
    const ficha = fichaBrecha().data;
    const prioridad = payloadOf<OpportunityListEnvelope>('listOportunidades.FAM-SIM-E3-00001.prioridad').items;
    const title = (id: string) => benefitName(id, [...prioridad, ...ficha.top_opportunities].find((o) => o.benefit_id === id)?.simple_title);
    const section = (name: string) => document.querySelector(`[data-benefit-section="${name}"]`) as HTMLElement;
    const titles = (name: string) => within(section(name)).getAllByRole('heading', { level: 3 }).map((h) => h.textContent);

    expect(await screen.findByRole('radio', { name: FAMILY_COPY.filterAll })).toBeChecked();
    // Orden de C3 `prioridad` (BEN-004 ASIGNADO va a "Ya postuló o sin cupo").
    const applyIds = prioridad.filter((o) => o.access_state === 'ELEGIBLE_SIN_ASIGNACION').map((o) => o.benefit_id);
    await waitFor(() => expect(titles('apply')).toEqual(applyIds.map(title)));
    expect(titles('missing')).toEqual([title('BEN-003')]);
    const showDone = within(section('done')).getByRole('button', { name: FAMILY_COPY.showDone });
    expect(showDone).toHaveAttribute('aria-expanded', 'false');
    expect(within(section('done')).getByRole('heading', { level: 3, hidden: true }).textContent).toBe(title('BEN-004'));

    // Tarjeta cerrada: bajo el nombre no va nada; al tocarla se ve el detalle.
    for (const chip of screen.getAllByText(t('group.go.label'))) expect(chip).not.toBeVisible();
    const card = within(section('missing')).getByRole('button', { name: title('BEN-003') });
    expect(card).toHaveAttribute('aria-expanded', 'false');
    await user.click(card);
    expect(card).toHaveAttribute('aria-expanded', 'true');
    expect(within(section('missing')).getByText(t('context.missing.last_health_control_date'))).toBeVisible();
    const question = ficha.top_opportunities.find((o) => o.benefit_id === 'BEN-003')?.suggested_questions[0] ?? '';
    expect(within(section('missing')).getByText(question)).toBeVisible();

    // "Qué hacer ahora": preguntar y entregar info de los que puede postular.
    const plan = document.querySelector('[data-action-plan]') as HTMLElement;
    expect(within(plan).getByText(question)).toBeInTheDocument();
    expect(within(plan).getByText(FAMILY_COPY.planDeliver(applyIds.map(title).join(', ')))).toBeInTheDocument();

    // Filtro: solo esa sección.
    await user.click(screen.getByRole('radio', { name: FAMILY_COPY.filterMissing('1') }));
    expect([...document.querySelectorAll('[data-benefit-section]')].map((s) => s.getAttribute('data-benefit-section'))).toEqual(['missing']);

    expect(screen.getByText(t('notice.referential'))).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/);
    expect(screen.getByRole('link', { name: t('family.actions.mark') })).toHaveAttribute('href', '/familias/FAM-SIM-E3-00001/conversacion');
  });

  it('SI pendiente sin códigos va a "Puede postular ahora" (PRELIMINAR en el detalle) sin pedir nada', async () => {
    const user = userEvent.setup();
    const clon = structuredClone(fichaBrecha());
    clon.data.benefit_results.push({ benefit_id: 'BEN-012', result: 'SI', level: 'PRELIMINAR', access_state: 'PENDIENTE_ANTECEDENTES', missing_codes: [], trace: [] });
    server.use(overrideOperation('getFamilia', () => HttpResponse.json(clon)));
    renderFamily();
    const name = benefitName('BEN-012', null);
    const apply = (await screen.findByRole('heading', { name: FAMILY_COPY.sectionApply })).closest('section') as HTMLElement;
    const toggle = await within(apply).findByRole('button', { name });
    await user.click(toggle);
    const card = toggle.closest('[data-benefit-card]') as HTMLElement;
    expect(within(card).getByText(t(LEVEL_KEY.PRELIMINAR))).toBeVisible();
    expect(within(card).queryByText(t(ACCESS_STATE_KEY.PENDIENTE_ANTECEDENTES))).toBeNull();

    await user.click(screen.getByRole('button', { name: ADD_INFO_COPY.householdTitle }));
    const household = document.querySelector('[data-household]') as HTMLElement;
    const plan = document.querySelector('[data-action-plan]') as HTMLElement;
    expect(household.textContent).not.toContain(name);
    expect(plan.querySelector('ul')?.textContent ?? '').not.toContain(name);
    expect(document.body.textContent).not.toMatch(/documento que confirme/i);
    expect(screen.queryByText(t('family.missing_generic'))).toBeNull();
  });

  it('DEC-038: el nombre de trato se guarda solo en este equipo y reemplaza el título genérico', async () => {
    const user = userEvent.setup();
    renderFamily('FAM-SIM-E3-00002');
    expect(await screen.findByRole('heading', { level: 1, name: t('family.generic_name', { short_id: '00002' }) })).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: t('family.name.open') }));
    await user.type(screen.getByLabelText(t('family.name.title')), '  Sofía   Ficticia ');
    await user.click(screen.getByRole('button', { name: t('family.name.save') }));
    // DEC-047: se guarda solo el primer nombre + inicial.
    expect(await screen.findByRole('heading', { level: 1, name: 'Sofía F.' })).toBeInTheDocument();
    expect(currentLocalNames().get('FAM-SIM-E3-00002')).toBe('Sofía F.');
    expect(screen.getByRole('link', { name: t('family.actions.add_info') })).toHaveAttribute('href', '/familias/FAM-SIM-E3-00002/agregar-informacion');
  });

  it('DEC-072: el ejemplo solo demo muestra su nombre, "Disponible en su comuna" y "Solo demo"; lo nacional no lleva chip', async () => {
    renderFamily('FAM-SIM-E3-00005');
    const heading = await screen.findByRole('heading', { level: 3, name: DEMO_TITLE });
    const card = heading.closest('[data-benefit-card]') as HTMLElement;
    expect(card.closest('[data-benefit-section]')).toHaveAttribute('data-benefit-section', 'apply');
    expect(within(card).getByText(LOCAL_CHIP)).toBeInTheDocument();
    expect(within(card).getByText(DEMO_LABEL)).toBeInTheDocument();
    expect(screen.getAllByText(LOCAL_CHIP)).toHaveLength(1);
    expect(screen.getAllByText(DEMO_LABEL)).toHaveLength(1);

    cleanup();
    renderFamily('FAM-SIM-E3-00001');
    await screen.findByRole('heading', { name: FAMILY_COPY.sectionApply });
    expect(screen.queryByText(LOCAL_CHIP)).toBeNull();
    expect(screen.queryByText(DEMO_LABEL)).toBeNull();
  });

  it('404 al cargar la ficha → mensaje seguro sin el texto del servidor', async () => {
    server.use(overrideOperation('getFamilia', () => HttpResponse.json(payloadOf('error.404'), { status: 404 })));
    renderFamily();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.not_found'))).toBeInTheDocument();
    expect(alert.textContent).not.toContain('Recurso inexistente');
  });
});

describe('FamilyPage con VITE_PROPOSAL_TERRITORIAL=false (DEC-072)', () => {
  beforeEach(() => {
    installTestRuntime();
    const off = resolveProfile({ VITE_PROFILE: 'local', VITE_USE_MOCKS: 'true', VITE_PROPOSAL_TERRITORIAL: 'false' }, { isSecureContext: true });
    if (!off.ok) throw new Error('territorial_off_config');
    configureRuntime(off.config);
  });
  afterEach(() => {
    server.events.removeAllListeners();
    cleanup();
    resetTestRuntime();
  });

  it('no muestra chip ni rótulo y no pide /catalogo/alcance', async () => {
    const paths: string[] = [];
    server.events.on('request:start', ({ request }) => {
      paths.push(new URL(request.url).pathname);
    });
    renderFamily('FAM-SIM-E3-00005');
    const applies = (await screen.findByRole('heading', { name: FAMILY_COPY.sectionApply })).closest('section') as HTMLElement;
    // BEN-001/002 y el ejemplo BEN-DEMO-LOCAL-01 (sin nombre de la propuesta: queda su ID); BEN-004
    // ASIGNADO va a "Ya postuló o sin cupo".
    await waitFor(() => expect(within(applies).getAllByRole('heading', { level: 3 })).toHaveLength(3));
    expect(screen.queryByText(LOCAL_CHIP)).toBeNull();
    expect(screen.queryByText(DEMO_LABEL)).toBeNull();
    expect(paths.some((p) => p.endsWith('/catalogo/alcance'))).toBe(false);
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
    await screen.findByRole('heading', { name: FAMILY_COPY.sectionApply });
    expect(document.querySelector('[data-name-editor]')).toBeNull();
    expect(screen.queryByLabelText(t('family.name.title'))).toBeNull();
    expect(screen.queryByRole('link', { name: t('family.actions.add_info') })).toBeNull();
    expect(screen.getByRole('link', { name: t('family.actions.mark') })).toBeInTheDocument();
  });
});
