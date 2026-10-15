// "Ya le informé" (B3, DEC-080): registra la conversación con UN toque. C3 1.0.2 sigue cerrado: el
// front completa el ConversationRequest con valores por defecto (frontend/README.md): los beneficios
// que se acaban de mostrar, siguiente paso NONE ("Por ahora nada", DEC-036), canal IN_PERSON y origen
// REAL_DEMO (SUP-033). Reutiliza la mutación y la cola offline de "Marcar conversado" (que sigue igual).
// El request lleva solo IDs y enums: nunca el nombre de trato local (DEC-038/DEC-047).
import { useState } from 'react';
import type { ConversationRequest } from '../../api/types';
import { useSubmitConversation, type ConversationOutcome } from '../../data/mutations';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { nowIsoWithOffset } from '../../lib/now';
import { uuid } from '../../lib/uuid';
import { Button } from '../../ui/Button';
import { Banner } from '../../ui/states';

/**
 * PROVISIONAL: excepción documentada a FE-004; ninguna clave de content/i18n/es.json dice "ya le
 * informé" y el catálogo está congelado; Rol 4 debe pasarlo a es.json (DEC-080).
 */
export const QUICK_INFORM_COPY = { button: 'Ya le informé' } as const;

/** Resultado → texto y tono del aviso (compartido con ConversationPage). */
export const OUTCOME_COPY: Readonly<
  Record<Exclude<ConversationOutcome, 'confirmed'>, { key: PlainCopyKey; tone: 'info' | 'warn' | 'danger' }>
> = {
  queued: { key: 'conversation.queued', tone: 'warn' },
  queue_disabled: { key: 'conversation.queue_disabled', tone: 'warn' },
  paused_auth: { key: 'conversation.paused_auth', tone: 'warn' },
  login_required: { key: 'auth.login_required.body', tone: 'warn' },
  conflict: { key: 'conversation.conflict', tone: 'warn' },
  unavailable: { key: 'conversation.unavailable', tone: 'danger' },
  rejected: { key: 'conversation.rejected', tone: 'danger' },
};

/** Resultados que se reintentan con el MISMO cuerpo y la MISMA clave. */
export const RETRY_SAME: ReadonlySet<ConversationOutcome> = new Set(['queue_disabled', 'unavailable']);

/** Cuerpo del toque único con los valores por defecto (DEC-080). */
export function quickInformBody(benefitIds: readonly string[], snapshotId: string): ConversationRequest {
  return {
    benefit_ids: [...new Set(benefitIds)],
    next_step: 'NONE',
    channel: 'IN_PERSON',
    occurred_at: nowIsoWithOffset(),
    snapshot_id: snapshotId,
    origin: 'REAL_DEMO',
  };
}

export interface QuickInformProps {
  readonly familyId: string;
  readonly gardenId: string;
  /** Beneficios que se acaban de mostrar (top_benefit_ids o top_opportunities de C3). */
  readonly benefitIds: readonly string[];
  readonly snapshotId: string;
  /** Ya conversada según el servidor: no se ofrece el botón. */
  readonly informed: boolean;
  readonly className?: string;
}

export function QuickInformButton({ familyId, gardenId, benefitIds, snapshotId, informed, className = '' }: QuickInformProps) {
  const mutation = useSubmitConversation();
  const [attempt, setAttempt] = useState<{ body: ConversationRequest; key: string } | null>(null);
  const [outcome, setOutcome] = useState<ConversationOutcome | null>(null);

  if (outcome === 'confirmed') {
    return (
      <p role="status" className="font-semibold text-go-ink">
        {t('conversation.success')}
      </p>
    );
  }
  if (informed || benefitIds.length === 0) return null;

  const send = () => {
    // Reintento tras 503/sin cola: mismo cuerpo y misma Idempotency-Key; si no, cuerpo y clave nuevos.
    const current =
      attempt !== null && outcome !== null && RETRY_SAME.has(outcome)
        ? attempt
        : { body: quickInformBody(benefitIds, snapshotId), key: uuid() };
    setAttempt(current);
    mutation
      .mutateAsync({ familyId, gardenId, body: current.body, idempotencyKey: current.key })
      .then(setOutcome)
      .catch(() => setOutcome('unavailable'));
  };

  const notice = outcome === null ? null : OUTCOME_COPY[outcome];
  // En cola o pausada: ya quedó guardada en el equipo; no se ofrece otro envío.
  const sent = outcome === 'queued' || outcome === 'paused_auth';

  return (
    <div className={`space-y-2 ${className}`.trim()}>
      {notice !== null && (
        <Banner tone={notice.tone} icon={sent ? 'clock' : 'alert'}>
          {t(notice.key)}
        </Banner>
      )}
      {!sent && (
        <Button variant="secondary" icon="check" className="w-full" busy={mutation.isPending} onClick={send}>
          {mutation.isPending
            ? t('conversation.sending')
            : outcome !== null && RETRY_SAME.has(outcome)
              ? t('conversation.retry')
              : QUICK_INFORM_COPY.button}
        </Button>
      )}
    </div>
  );
}
