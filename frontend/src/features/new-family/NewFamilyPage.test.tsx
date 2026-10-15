// Familia nueva con el mock-servidor C3. Respuestas inventadas para la prueba; datos 100 % sintéticos
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { PreevaluationEnvelope, PreevaluationRequest } from '../../api/types';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { resetClock, setClock } from '../../lib/now';
import { payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import NewFamilyPage from './NewFamilyPage';

function renderNewFamily() {
  return renderWithProviders(
    <Routes>
      <Route path="/familia-nueva" element={<NewFamilyPage />} />
    </Routes>,
    { route: '/familia-nueva' },
  );
}

const groupNamed = (key: PlainCopyKey) => screen.getByRole('group', { name: t(key) });

describe('NewFamilyPage', () => {
  beforeEach(() => {
    installTestRuntime();
    setClock(() => Date.parse('2026-10-14T10:00:00-03:00'));
  });
  afterEach(() => {
    resetClock();
    resetTestRuntime();
  });

  it('preguntas cerradas con "No sé" → cuerpo explícito con null/UNKNOWN y resultado PRELIMINAR', async () => {
    const user = userEvent.setup();
    const bodies: PreevaluationRequest[] = [];
    server.use(
      overrideOperation('createPreevaluacion', async ({ request }) => {
        bodies.push((await request.json()) as PreevaluationRequest);
        return HttpResponse.json(payloadOf('createPreevaluacion'), { status: 200 });
      }),
    );
    renderNewFamily();

    const next = await screen.findByRole('button', { name: t('common.continue') });
    expect(next).toBeDisabled(); // aviso Demo obligatorio
    await user.click(screen.getByRole('checkbox', { name: new RegExp(t('new_family.demo_notice_accept')) }));
    await user.selectOptions(screen.getByLabelText(t('new_family.q.child_age')), '4');
    await user.click(next);

    await user.click(within(groupNamed('new_family.q.has_rsh')).getByRole('radio', { name: t('common.dont_know') }));
    expect(screen.queryByRole('group', { name: t('new_family.q.rsh_band') })).toBeNull();
    await user.click(screen.getByRole('button', { name: t('common.continue') }));

    await user.click(within(groupNamed('new_family.q.housing_type')).getByRole('radio', { name: t('common.dont_know') }));
    await user.click(within(groupNamed('new_family.q.child_in_therapy')).getByRole('radio', { name: t('common.no') }));
    await user.click(screen.getByRole('button', { name: t('common.continue') }));
    await user.click(screen.getByRole('button', { name: t('common.continue') }));

    expect(screen.getByRole('heading', { name: t('new_family.step.review') })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: t('new_family.submit') }));

    expect(await screen.findByRole('heading', { name: t('new_family.result_title') })).toBeInTheDocument();
    const result = payloadOf<PreevaluationEnvelope>('createPreevaluacion').data;
    expect(screen.getByRole('heading', { level: 3, name: result.opportunities[0]?.simple_title })).toBeInTheDocument();
    expect(screen.getByText(t('notice.referential'))).toBeInTheDocument();

    expect(bodies).toHaveLength(1);
    const body = bodies[0] as PreevaluationRequest;
    expect(Object.keys(body)).toHaveLength(22); // todas las claves de PreevaluationRequest
    expect(body).toMatchObject({
      data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON',
      garden_id: 'JAR-SIM-E3-00001',
      commune_id: 'COM-001',
      demo_notice_accepted: true,
      child_age: 4,
      siblings_under_6: null,
      has_rsh: null,
      rsh_band: null,
      housing_type: 'UNKNOWN',
      child_in_therapy: false,
      last_child_health_control_date: null,
    });
  }, 20_000); // recorre los 5 pasos con userEvent: con la suite completa en paralelo supera los 5 s por defecto

  it('una fecha de control futura muestra el error en línea y no deja continuar', async () => {
    const user = userEvent.setup();
    renderNewFamily();
    await user.click(await screen.findByRole('checkbox', { name: new RegExp(t('new_family.demo_notice_accept')) }));
    await user.click(screen.getByRole('button', { name: t('common.continue') }));
    await user.click(screen.getByRole('button', { name: t('common.continue') }));

    const date = screen.getByLabelText(t('new_family.q.last_child_health_control_date'));
    fireEvent.change(date, { target: { value: '2026-12-01' } });
    expect(screen.getByRole('alert')).toHaveTextContent(t('new_family.date_future'));
    expect(date).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('button', { name: t('common.continue') })).toBeDisabled();
  });
});
