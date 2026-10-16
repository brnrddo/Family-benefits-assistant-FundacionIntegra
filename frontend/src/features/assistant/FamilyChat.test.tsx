// Chat de la ficha con el mock-servidor C3. Nombres y preguntas inventados; datos 100 % sintéticos
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { afterEach, describe, expect, it } from 'vitest';
import type { AssistantEnvelope } from '../../api/types';
import { clearDemoData } from '../../offline/db';
import { clearLocalNamesMemory, refreshLocalNames, saveLocalName } from '../../offline/localNames';
import { payloadOf } from '../../test/fixtures';
import { server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import { DEMO_COPY } from '../demo-session/demoCopy';
import { FamilyChat } from './FamilyChat';

describe('FamilyChat', () => {
  afterEach(async () => {
    clearLocalNamesMemory();
    await clearDemoData();
    resetTestRuntime();
  });

  it('compone una pregunta ≤500 con "Contexto de la familia:" y cambia el nombre local antes de enviar', async () => {
    installTestRuntime({ persistence: true });
    await clearDemoData();
    expect((await saveLocalName('FAM-SIM-E3-00002', 'Sofía Ficticia')).ok).toBe(true);
    await refreshLocalNames();
    let captured: { question?: string } = {};
    server.use(
      overrideOperation('askCatalogAssistant', async ({ request }) => {
        captured = (await request.json()) as { question?: string };
        return HttpResponse.json(payloadOf('askCatalogAssistant.catalog-info'));
      }),
    );
    renderWithProviders(<FamilyChat familyId="FAM-SIM-E3-00002" />);
    const user = userEvent.setup();
    const submit = screen.getByRole('button', { name: DEMO_COPY.familyChatSubmit });
    await user.type(screen.getByLabelText(DEMO_COPY.familyChatLabel), 'Hoy sofia llegó triste: la mamá está embarazada y quedó sin trabajo');
    await expect.poll(() => submit.hasAttribute('disabled')).toBe(false);
    await user.click(submit);

    const envelope = payloadOf<AssistantEnvelope>('askCatalogAssistant.catalog-info');
    expect(await screen.findByText((_, el) => el?.textContent === envelope.answer && el.classList.contains('c3-text'))).toBeInTheDocument();
    const q = captured.question ?? '';
    expect(q.startsWith('Contexto de la familia:')).toBe(true);
    expect(q).toContain('Situación que cuenta la tía:');
    expect(q).toContain('el niño o la niña');
    expect([...q].length).toBeLessThanOrEqual(500);
    expect(q.toLowerCase()).not.toMatch(/sofía|sofia|ficticia/);
  });
});
