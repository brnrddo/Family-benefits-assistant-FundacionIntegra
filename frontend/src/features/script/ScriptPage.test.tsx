// Guion con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { ScriptGenerationEnvelope } from '../../api/types';
import { t } from '../../i18n/copy';
import { payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import ScriptPage from './ScriptPage';

function renderScript() {
  return renderWithProviders(
    <Routes>
      <Route path="/familias/:familyId/guion" element={<ScriptPage />} />
    </Routes>,
    { route: '/familias/FAM-SIM-E3-00001/guion' },
  );
}

describe('ScriptPage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => resetTestRuntime());

  it('muestra el guion como texto, el proveedor, el aviso y la acción de marcar conversado', async () => {
    renderScript();
    const script = payloadOf<ScriptGenerationEnvelope>('createGuion.bedrock').content.script;
    const firstLine = script.split('\n')[0] ?? '';
    const text = await screen.findByText((_content, node) => node?.tagName === 'P' && (node.textContent ?? '').startsWith(firstLine));
    expect(text).toHaveClass('c3-text');
    expect(screen.getByText(t('data.provider.bedrock'))).toBeInTheDocument();
    expect(screen.getByText(t('notice.referential'))).toBeInTheDocument();
    expect(screen.getByRole('link', { name: t('family.actions.mark') })).toHaveAttribute('data-primary-action');
  });

  it('503 al generar → mensaje seguro con Reintentar', async () => {
    server.use(overrideOperation('createGuion', () => HttpResponse.json(payloadOf('error.503'), { status: 503 })));
    renderScript();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.unavailable'))).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: t('common.retry') })).toBeInTheDocument();
  });
});
