// "Agregar información" (DEC-039, operación PROPUESTA) con el mock-servidor. Datos 100 % sintéticos
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import { getAntecedentesFixture as antecedentesFixture, addInfoEngineCodes as engineCodes } from '../../api/proposals/testFixtures';
import { t } from '../../i18n/copy';
import { server, TEST_API_BASE } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import { FAMILY_COPY } from '../family/familyCopy';
import FamilyPage from '../family/FamilyPage';
import AddInfoPage from './AddInfoPage';

const FAMILY = 'FAM-SIM-E3-00002';

describe('AddInfoPage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => {
    server.events.removeAllListeners();
    resetTestRuntime();
  });

  it('solo pregunta lo que falta, envía campos cerrados y vuelve a la ficha refrescada (PRELIMINAR)', async () => {
    const user = userEvent.setup();
    const bodies: unknown[] = [];
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'POST' && request.url.endsWith(`/familias/${FAMILY}/antecedentes`)) {
        void request.clone().json().then((body: unknown) => bodies.push(body));
      }
    });
    renderWithProviders(
      <Routes>
        <Route path="/familias/:familyId" element={<FamilyPage />} />
        <Route path="/familias/:familyId/agregar-informacion" element={<AddInfoPage />} />
      </Routes>,
      { route: `/familias/${FAMILY}/agregar-informacion` },
    );
    // Faltan rsh_status (→ has_rsh) e income_band (→ household_income_band): solo esas dos preguntas, con "No sé".
    const rsh = await screen.findByRole('group', { name: t('new_family.q.has_rsh') });
    const income = screen.getByRole('group', { name: t('new_family.q.household_income_band') });
    expect(screen.getAllByRole('group')).toHaveLength(2);
    expect(within(rsh).getByRole('radio', { name: t('common.dont_know') })).toBeInTheDocument();
    expect(document.querySelector('textarea, input[type="text"]')).toBeNull();

    await user.click(within(rsh).getByRole('radio', { name: t('common.yes') }));
    await user.click(within(income).getByRole('radio', { name: t('income_band.under_110k') }));
    await user.click(screen.getByRole('button', { name: t('add_info.submit') }));

    // Resultado según el recálculo: nombres legibles bajo "Ahora aplica", nunca códigos internos.
    const result = await screen.findByRole('status');
    const nowApplies = within(result).getByRole('heading', { name: ADD_INFO_COPY.nowApplies }).parentElement as HTMLElement;
    expect(within(nowApplies).getByText(/Control de salud infantil/)).toBeInTheDocument();
    expect(within(nowApplies).getByText(/Subsidio para el agua/)).toBeInTheDocument();
    expect(result.textContent).not.toMatch(/\b(BEN|FAM)-/);
    await user.click(within(result).getByRole('button', { name: ADD_INFO_COPY.backToFamily }));

    expect(await screen.findByText(t('family.add_info_done'))).toBeInTheDocument();
    expect(bodies).toEqual([{ data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON', has_rsh: true, household_income_band: 'UNDER_110K' }]);
    // Ya no falta nada: la sección "Falta información" no aparece y los tres quedan en "Puede postular ahora".
    expect(document.querySelector('[data-benefit-section="missing"]')).toBeNull();
    const applies = screen.getByRole('heading', { name: FAMILY_COPY.sectionApply }).closest('section') as HTMLElement;
    expect(within(applies).getAllByText(t('level.preliminar'))).toHaveLength(3);
  });

  it('no vuelve a preguntar los campos ya declarados (GET /antecedentes declared_fields)', async () => {
    const declared = structuredClone(antecedentesFixture.payload);
    server.use(
      http.get(`${TEST_API_BASE}/familias/:id/antecedentes`, () =>
        HttpResponse.json({ ...declared, data: { ...declared.data, declared_fields: ['has_rsh'] } }),
      ),
    );
    renderWithProviders(
      <Routes>
        <Route path="/familias/:familyId/agregar-informacion" element={<AddInfoPage />} />
      </Routes>,
      { route: `/familias/${FAMILY}/agregar-informacion` },
    );
    expect(await screen.findByRole('group', { name: t('new_family.q.household_income_band') })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: t('new_family.q.has_rsh') })).toBeNull();
    expect(screen.getAllByRole('group')).toHaveLength(1);
  });

  const renderEngineCodes = (antecedentes: () => Response) => {
    server.use(
      overrideOperation('getFamilia', () => HttpResponse.json(engineCodes.ficha)),
      http.get(`${TEST_API_BASE}/familias/:id/antecedentes`, antecedentes),
    );
    renderWithProviders(
      <Routes>
        <Route path="/familias/:familyId/agregar-informacion" element={<AddInfoPage />} />
      </Routes>,
      { route: `/familias/${FAMILY}/agregar-informacion` },
    );
  };

  it('códigos del motor: semanas_gestacion → una pregunta Sí/No/No sé, sin preguntas ni guías repetidas; N del GET previo', async () => {
    const user = userEvent.setup();
    renderEngineCodes(() => HttpResponse.json(engineCodes.antecedentes));
    // semanas_gestacion aparece en dos beneficios: UNA sola pregunta de embarazo (opcional, en la leyenda).
    const pregnancy = await screen.findByRole('group', { name: ADD_INFO_COPY.optionalSensitive(t('new_family.q.household_pregnancy')) });
    for (const option of [t('common.yes'), t('common.no'), t('common.dont_know')]) {
      expect(within(pregnancy).getByRole('radio', { name: option })).toBeInTheDocument();
    }
    const legends = () => screen.getAllByRole('group').map((group) => group.querySelector('legend')?.textContent ?? '');
    expect(new Set(legends()).size).toBe(legends().length);
    expect(screen.queryByText(t('add_info.no_fields'))).toBeNull();
    expect(screen.queryByText(t('family.missing_generic'))).toBeNull();
    // La guía (documento_terapia_dias, sin campo cerrado) no repite líneas.
    const guide = screen.getByRole('heading', { name: t('add_info.guide_title') }).closest('div') as HTMLElement;
    const lines = within(guide).getAllByRole('listitem').map((item) => item.textContent);
    expect(lines.length).toBeGreaterThan(0);
    expect(new Set(lines).size).toBe(lines.length);

    // "Sí" abre la pregunta de semanas con el umbral N que entregó GET /antecedentes.
    await user.click(within(pregnancy).getByRole('radio', { name: t('common.yes') }));
    expect(await screen.findByRole('group', { name: ADD_INFO_COPY.optionalSensitive(ADD_INFO_COPY.pregnancyWeeksN('20')) })).toBeInTheDocument();
    expect(new Set(legends()).size).toBe(legends().length);
  });

  it('modo mock: la pregunta de semanas muestra N del handler MSW', async () => {
    const user = userEvent.setup();
    // Sin override del GET: responde el handler MSW de GET /familias/:id/antecedentes.
    server.use(overrideOperation('getFamilia', () => HttpResponse.json(engineCodes.ficha)));
    renderWithProviders(
      <Routes>
        <Route path="/familias/:familyId/agregar-informacion" element={<AddInfoPage />} />
      </Routes>,
      { route: `/familias/${FAMILY}/agregar-informacion` },
    );
    const pregnancy = await screen.findByRole('group', { name: ADD_INFO_COPY.optionalSensitive(t('new_family.q.household_pregnancy')) });
    await user.click(within(pregnancy).getByRole('radio', { name: t('common.yes') }));
    const weeks = String(antecedentesFixture.payload.data.pregnancy_weeks_threshold);
    expect(await screen.findByRole('group', { name: ADD_INFO_COPY.optionalSensitive(ADD_INFO_COPY.pregnancyWeeksN(weeks)) })).toBeInTheDocument();
  });

  it('sin umbral (GET /antecedentes falla): la pregunta de semanas no lleva número', async () => {
    const user = userEvent.setup();
    renderEngineCodes(() => new HttpResponse(null, { status: 503 }));
    const pregnancy = await screen.findByRole('group', { name: ADD_INFO_COPY.optionalSensitive(t('new_family.q.household_pregnancy')) });
    await user.click(within(pregnancy).getByRole('radio', { name: t('common.yes') }));
    const weeks = screen.getByRole('group', { name: ADD_INFO_COPY.optionalSensitive(ADD_INFO_COPY.pregnancyWeeksMin) });
    expect(weeks.querySelector('legend')?.textContent).not.toMatch(/\d/);
  });
});
