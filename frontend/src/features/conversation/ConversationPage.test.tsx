// Marcar conversado con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { getKpi } from '../../api/client';
import { t } from '../../i18n/copy';
import { listQueue } from '../../offline/conversationQueue';
import { clearDemoData } from '../../offline/db';
import { fichaBrecha, jardines, payloadOf } from '../../test/fixtures';
import { mockServer, server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import ConversationPage from './ConversationPage';

const FAMILY = 'FAM-SIM-E3-00001';

function renderConversation() {
  return renderWithProviders(
    <Routes>
      <Route path="/familias/:familyId/conversacion" element={<ConversationPage />} />
    </Routes>,
    { route: `/familias/${FAMILY}/conversacion` },
  );
}

describe('ConversationPage', () => {
  afterEach(() => resetTestRuntime());

  describe('en línea', () => {
    beforeEach(() => installTestRuntime());

    it('tres toques: top y canal preseleccionados, siguiente paso y confirmar → 201 del servidor', async () => {
      const user = userEvent.setup();
      expect(mockServer.snapshotOfState().informed).not.toContain(FAMILY);
      renderConversation();
      const confirm = await screen.findByRole('button', { name: t('conversation.confirm') });
      expect(confirm).toBeDisabled();
      for (const o of fichaBrecha().data.top_opportunities) {
        expect(await screen.findByRole('checkbox', { name: o.simple_title })).toBeChecked();
      }
      expect(screen.getByRole('radio', { name: t('channel.in_person') })).toBeChecked();
      expect(screen.getByText(t('conversation.no_free_text_note'))).toBeInTheDocument();
      expect(document.querySelector('textarea, input[type="text"]')).toBeNull();

      await user.click(screen.getByRole('radio', { name: t('next_step.go_to_institution') }));
      await user.click(confirm);

      expect(await screen.findByText(t('conversation.success'))).toBeInTheDocument();
      expect(mockServer.snapshotOfState().informed).toContain(FAMILY);
    });

    it('503 → reintento con la MISMA Idempotency-Key; otro cuerpo usa otra clave', async () => {
      const user = userEvent.setup();
      const keys: (string | null)[] = [];
      server.use(
        overrideOperation('createConversacion', ({ request }) => {
          keys.push(request.headers.get('Idempotency-Key'));
          return HttpResponse.json(payloadOf('error.503'), { status: 503 });
        }),
      );
      renderConversation();
      await user.click(await screen.findByRole('radio', { name: t('next_step.bring_documents') }));
      await user.click(screen.getByRole('button', { name: t('conversation.confirm') }));
      expect(await screen.findByText(t('conversation.unavailable'))).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: t('conversation.retry') }));
      await waitFor(() => expect(keys).toHaveLength(2));
      expect(keys[1]).toBe(keys[0]);
      await screen.findByRole('button', { name: t('conversation.retry') });

      await user.click(screen.getByRole('radio', { name: t('next_step.update_rsh') }));
      await user.click(screen.getByRole('button', { name: t('conversation.confirm') }));
      await waitFor(() => expect(keys).toHaveLength(3));
      expect(keys[2]).not.toBe(keys[0]);
    });
  });

  describe('sin red en Demo', () => {
    beforeEach(async () => {
      installTestRuntime({ persistence: true });
      await clearDemoData();
    });
    afterEach(() => clearDemoData());

    it('queda en la cola local y el KPI del servidor NO sube', async () => {
      const user = userEvent.setup();
      server.use(overrideOperation('createConversacion', () => HttpResponse.error()));
      renderConversation();
      await user.click(await screen.findByRole('radio', { name: t('next_step.go_to_institution') }));
      await user.click(screen.getByRole('button', { name: t('conversation.confirm') }));

      expect(await screen.findByText(t('conversation.queued'))).toBeInTheDocument();
      expect(await screen.findByRole('heading', { name: t('queue.title') })).toBeInTheDocument();
      const [entry] = await listQueue();
      expect(entry?.family_id).toBe(FAMILY);
      expect(entry?.status).toBe('EN_ESPERA');

      const kpi = await getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-00001' });
      expect(kpi.body.data.informed_families).toBe(jardines().items[0]?.families_informed);
      expect(mockServer.snapshotOfState().informed).not.toContain(FAMILY);
    });
  });
});
