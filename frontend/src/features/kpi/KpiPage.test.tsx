// Avance / KPI con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { KpiEnvelope } from '../../api/types';
import { formatClp, formatInteger, formatPercent } from '../../domain/format';
import { benefitName, t } from '../../i18n/copy';
import { payloadOf } from '../../test/fixtures';
import { mockServer, server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import KpiPage from './KpiPage';

function renderKpi() {
  return renderWithProviders(
    <Routes>
      <Route path="/avance" element={<KpiPage />} />
    </Routes>,
    { route: '/avance' },
  );
}

const ratio = (informed: number, total: number) => t('kpi.ratio', { informed: formatInteger(informed), total: formatInteger(total) });

describe('KpiPage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => resetTestRuntime());

  it('muestra los agregados de C3 tal cual; null → "Sin dato" y nunca 0', async () => {
    renderKpi();
    const kpi = payloadOf<KpiEnvelope>('getKpi').data;
    expect(await screen.findByText(ratio(kpi.informed_families, kpi.total_families))).toBeInTheDocument();
    expect(screen.getByText(formatPercent(kpi.informed_percentage ?? -1))).toBeInTheDocument();
    // Sin familias nuevas, C3 entrega informed_new_percentage = null.
    expect(screen.getAllByText(t('common.not_available')).length).toBeGreaterThan(0);
    const [gap] = kpi.top_gaps;
    expect(screen.getByText(benefitName(gap?.benefit_id ?? ''))).toBeInTheDocument();
    expect(screen.getByText(t('kpi.gap_amount', { amount: formatClp(gap?.potential_annual_amount ?? 0) }))).toBeInTheDocument();
    expect(document.querySelector('[data-primary-action]')).toBeNull();
  });

  it('suppressed: true → ninguna cifra del payload, solo el aviso', async () => {
    mockServer.setScenario('kpiSuppressed');
    renderKpi();
    expect(await screen.findByText(t('kpi.suppressed'))).toBeInTheDocument();
    const kpi = payloadOf<KpiEnvelope>('getKpi.suppressed').data;
    const main = document.body.textContent ?? '';
    expect(main).not.toContain(ratio(kpi.informed_families, kpi.total_families));
    expect(main).not.toContain(t('kpi.gap_families', { count: formatInteger(kpi.top_gaps[0]?.family_count ?? 0) }));
    expect(main).not.toContain(t('kpi.informed'));
    expect(document.querySelectorAll('progress')).toHaveLength(0);
  });

  it('rango "desde" posterior a "hasta" → error en línea y sin consultar', async () => {
    const user = userEvent.setup();
    const urls: string[] = [];
    server.use(
      overrideOperation('getKpi', ({ request }) => {
        urls.push(request.url);
        return HttpResponse.json(payloadOf('getKpi'), { status: 200 });
      }),
    );
    renderKpi();
    await screen.findByText(t('kpi.informed'));
    fireEvent.change(screen.getByLabelText(t('kpi.from_label')), { target: { value: '2026-10-10' } });
    fireEvent.change(screen.getByLabelText(t('kpi.to_label')), { target: { value: '2026-10-01' } });
    await user.click(screen.getByRole('button', { name: t('kpi.apply') }));
    expect(screen.getByRole('alert')).toHaveTextContent(t('kpi.range_invalid'));
    expect(screen.getByLabelText(t('kpi.to_label'))).toHaveAttribute('aria-invalid', 'true');
    expect(urls.some((url) => url.includes('desde='))).toBe(false);
  });
});
