// B3 "Ya le informé" (DEC-080) con el mock-servidor C3. Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { t } from '../../i18n/copy';
import { mockServer, server } from '../../test/mswServer';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import HomePage from '../home/HomePage';
import { listOpen } from '../demo-session/demoCopy';
import { QUICK_INFORM_COPY } from './QuickInform';

const FAMILY = 'FAM-SIM-E3-00002';

describe('QuickInformButton', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => resetTestRuntime());

  it('un toque en Inicio envía los defaults de DEC-080 y la tarjeta queda conversada', async () => {
    const user = userEvent.setup();
    const bodies: unknown[] = [];
    const onRequest = ({ request }: { request: Request }) => {
      if (request.method === 'POST' && request.url.includes('/conversaciones')) {
        void request.clone().json().then((body) => bodies.push(body));
      }
    };
    server.events.on('request:start', onRequest);
    try {
      expect(mockServer.snapshotOfState().informed).not.toContain(FAMILY);
      renderWithProviders(
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>,
        { route: '/' },
      );
      // La lista viene plegada (DEC-091).
      await user.click(await screen.findByRole('button', { name: listOpen(8) }));
      const link = await screen.findByRole('link', { name: new RegExp(t('family.generic_name', { short_id: '00002' })) });
      const row = link.closest('li') as HTMLElement;
      // Una familia ya conversada no ofrece el botón.
      const done = screen.getByRole('link', { name: new RegExp(t('family.generic_name', { short_id: '00005' })) });
      expect(within(done.closest('li') as HTMLElement).queryByRole('button')).toBeNull();

      await user.click(within(row).getByRole('button', { name: QUICK_INFORM_COPY.button }));

      expect(await within(row).findByText(t('conversation.success'))).toBeInTheDocument();
      await waitFor(() => expect(bodies).toHaveLength(1));
      expect(bodies[0]).toMatchObject({
        benefit_ids: ['BEN-003', 'BEN-005', 'BEN-006'],
        next_step: 'NONE',
        channel: 'IN_PERSON',
        origin: 'REAL_DEMO',
      });
      expect(Object.keys(bodies[0] as object).sort()).toEqual(['benefit_ids', 'channel', 'next_step', 'occurred_at', 'origin', 'snapshot_id']);
      expect(mockServer.snapshotOfState().informed).toContain(FAMILY);
      expect(await within(row).findByText(new RegExp(t('conversation_status.conversada')))).toBeInTheDocument();
    } finally {
      server.events.removeListener('request:start', onRequest);
    }
  });
});
