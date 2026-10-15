// Panel de conversaciones por enviar (solo Demo con cola, design.md §12.4). Lo pendiente vive solo
// en este equipo y NO cuenta en el avance: solo un 201 del servidor confirma (FE-006).
import { useQueryClient } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { runtimeConfig } from '../../config/profile';
import { drainAndRefresh } from '../../data/sync';
import { familyDisplayName } from '../../domain/familyName';
import { formatInteger } from '../../domain/format';
import type { Tone } from '../../domain/presentation';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { discardEntry, useQueueSummary } from '../../offline/conversationQueue';
import type { QueueStatus } from '../../offline/db';
import { useLocalNames } from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import type { UiIconName } from '../../ui/icons';

const STATUS_PRESENTATION: Readonly<Record<QueueStatus, { labelKey: PlainCopyKey; icon: UiIconName; tone: Tone }>> = {
  EN_ESPERA: { labelKey: 'queue.status.pending', icon: 'clock', tone: 'ask' },
  PAUSADA_AUTH: { labelKey: 'queue.status.paused_auth', icon: 'user', tone: 'ask' },
  CONFLICTO: { labelKey: 'queue.status.conflict', icon: 'alert', tone: 'other' },
  REINTENTO_MANUAL: { labelKey: 'queue.status.unavailable', icon: 'refresh', tone: 'ask' },
  RECHAZADA: { labelKey: 'queue.status.rejected', icon: 'dash', tone: 'neutral' },
};

/** Estados que ya no se envían solos: la tía puede descartarlos. */
const DISCARDABLE: ReadonlySet<QueueStatus> = new Set(['CONFLICTO', 'REINTENTO_MANUAL', 'RECHAZADA']);

export function QueuePanel() {
  const queueEnabled = runtimeConfig().capabilities.queue;
  const queue = useQueueSummary();
  const names = useLocalNames();
  const queryClient = useQueryClient();
  const [sending, setSending] = useState(false);
  const titleId = useId();
  if (!queueEnabled || queue.entries.length === 0) return null;

  const sendNow = async () => {
    setSending(true);
    try {
      await drainAndRefresh(queryClient, true);
    } finally {
      setSending(false);
    }
  };

  return (
    <section aria-labelledby={titleId} className={`${CARD_CLASS} space-y-3`}>
      <h2 id={titleId}>{t('queue.title')}</h2>
      <p>{t('queue.count', { count: formatInteger(queue.entries.length) })}</p>
      <ul className="space-y-2">
        {queue.entries.map((entry) => {
          const status = STATUS_PRESENTATION[entry.status];
          return (
            <li key={entry.idempotency_key} className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{familyDisplayName(entry.family_id, names)}</span>
              <Chip icon={status.icon} tone={status.tone} label={t(status.labelKey)} />
              {DISCARDABLE.has(entry.status) && (
                <Button variant="ghost" size="sm" onClick={() => void discardEntry(entry.idempotency_key)}>
                  {t('conversation.discard')}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
      <Button variant="secondary" icon="refresh" busy={sending} className="w-full" onClick={() => void sendNow()}>
        {t('queue.send_now')}
      </Button>
      {sending && (
        <p role="status" className="text-ink-muted">
          {t('conversation.sending')}
        </p>
      )}
    </section>
  );
}
