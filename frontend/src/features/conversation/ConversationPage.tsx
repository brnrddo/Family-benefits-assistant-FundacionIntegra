// Marcar conversado en tres toques (design.md §9.4, FE-002/FE-006/FE-007): (1) "Marcar conversado"
// en la ficha o el guion, (2) siguiente paso, (3) "Confirmar conversación". Beneficios del top de C3
// y canal "En persona" llegan ya marcados (editables). Sin texto libre, nombres ni contacto.
// La barra y el KPI suben SOLO con datos del servidor (201); una conversación en cola no cuenta.
import { useState } from 'react';
import { useParams } from 'react-router';
import type { Channel, ConversationRequest, FamilyDetail, NextStep, Opportunity } from '../../api/types';
import { useSubmitConversation, type ConversationOutcome } from '../../data/mutations';
import { useFamilia, useOportunidades } from '../../data/queries';
import { familyDisplayName } from '../../domain/familyName';
import { isValidId } from '../../domain/ids';
import { CHANNEL_KEY, NEXT_STEP_KEY } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { nowIsoWithOffset } from '../../lib/now';
import { uuid } from '../../lib/uuid';
import { useLocalNames } from '../../offline/localNames';
import { Button, ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { CheckList, ChoiceChips } from '../../ui/ChoiceChips';
import { DataFreshness } from '../../ui/DataStatus';
import { PageTitle } from '../../ui/PageTitle';
import { Banner, EmptyState, ErrorState, Skeleton } from '../../ui/states';
import { familyRoutes } from '../family/routes';
import NotFoundPage from '../system/NotFoundPage';
import { QueuePanel } from './QueuePanel';
// Avisos por resultado (`confirmed` usa su propia vista) y reintentos con la misma clave.
import { OUTCOME_COPY, RETRY_SAME } from './QuickInform';

const NEXT_STEPS: readonly NextStep[] = ['GO_TO_INSTITUTION', 'UPDATE_RSH', 'BRING_DOCUMENTS', 'NONE'];
const CHANNELS: readonly Channel[] = ['IN_PERSON', 'GROUP_MEETING', 'WHATSAPP_PREVIEW', 'PRINTED'];

/** Un envío: mismo cuerpo ⇒ misma Idempotency-Key en cada reintento (§9.4). */
interface Attempt {
  readonly selection: string;
  readonly body: ConversationRequest;
  readonly key: string;
}

interface FormProps {
  readonly detail: FamilyDetail;
  readonly snapshotId: string;
  readonly options: readonly Opportunity[];
}

function ConversationForm({ detail, snapshotId, options }: FormProps) {
  const familyId = detail.family_id;
  const [selected, setSelected] = useState<ReadonlySet<string>>(() => new Set(detail.top_opportunities.map((o) => o.benefit_id)));
  const [channel, setChannel] = useState<Channel>('IN_PERSON');
  const [nextStep, setNextStep] = useState<NextStep | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [outcome, setOutcome] = useState<ConversationOutcome | null>(null);
  const mutation = useSubmitConversation();
  const homeLink = `/?${new URLSearchParams({ jardin: detail.garden_id }).toString()}`;

  // IDs en el orden de C3 (lista `prioridad`), sin duplicados.
  const benefitIds = options.map((o) => o.benefit_id).filter((id) => selected.has(id));
  const canConfirm = benefitIds.length > 0 && nextStep !== null && !mutation.isPending;

  const toggle = (benefitId: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(benefitId)) next.delete(benefitId);
      else next.add(benefitId);
      return next;
    });
    setOutcome(null);
  };

  const send = (current: Attempt) => {
    setAttempt(current);
    mutation
      .mutateAsync({ familyId, gardenId: detail.garden_id, body: current.body, idempotencyKey: current.key })
      .then((result) => {
        setOutcome(result);
        // 409 refresca la ficha (otro snapshot) y 4xx no se reintentan: el próximo envío usa otra clave.
        if (result === 'confirmed' || result === 'conflict' || result === 'rejected') setAttempt(null);
      })
      .catch(() => setOutcome('unavailable'));
  };

  const confirm = () => {
    if (nextStep === null || benefitIds.length === 0) return;
    const selection = JSON.stringify([benefitIds, nextStep, channel, snapshotId]);
    if (attempt !== null && attempt.selection === selection) {
      send(attempt);
      return;
    }
    send({
      selection,
      key: uuid(),
      body: {
        benefit_ids: benefitIds,
        next_step: nextStep,
        channel,
        occurred_at: nowIsoWithOffset(),
        snapshot_id: snapshotId,
        origin: 'REAL_DEMO',
      },
    });
  };

  const discard = () => {
    setAttempt(null);
    setOutcome(null);
    setNextStep(null);
  };

  if (outcome === 'confirmed') {
    return (
      <Card className="space-y-4">
        <p role="status" className="text-lg font-bold text-go-ink">
          {t('conversation.success')}
        </p>
        <ButtonLink to={homeLink} icon="home" data-primary-action className="w-full">
          {t('notfound.back_home')}
        </ButtonLink>
        <ButtonLink to={familyRoutes.ficha(familyId)} variant="secondary" className="w-full">
          {t('nav.back')}
        </ButtonLink>
      </Card>
    );
  }

  if (outcome === 'queued' || outcome === 'paused_auth') {
    return (
      <div className="space-y-4">
        <Banner tone="warn" icon="clock">
          {t(OUTCOME_COPY[outcome].key)}
        </Banner>
        <QueuePanel />
        <ButtonLink to={homeLink} icon="home" data-primary-action className="w-full">
          {t('notfound.back_home')}
        </ButtonLink>
      </div>
    );
  }

  const notice = outcome === null ? null : OUTCOME_COPY[outcome];

  return (
    <div className="space-y-5">
      <CheckList
        legend={t('conversation.benefits_label')}
        options={options.map((o) => ({ value: o.benefit_id, label: benefitName(o.benefit_id, o.simple_title) }))}
        values={selected}
        onToggle={toggle}
      />
      {benefitIds.length === 0 && <p className="text-danger-ink">{t('conversation.select_at_least_one')}</p>}

      <ChoiceChips
        legend={t('conversation.next_step_label')}
        options={NEXT_STEPS.map((value) => ({ value, label: t(NEXT_STEP_KEY[value]) }))}
        value={nextStep}
        onChange={(value) => {
          setNextStep(value as NextStep);
          setOutcome(null);
        }}
      />

      <ChoiceChips
        legend={t('conversation.channel_label')}
        options={CHANNELS.map((value) => ({ value, label: t(CHANNEL_KEY[value]) }))}
        value={channel}
        onChange={(value) => {
          setChannel(value as Channel);
          setOutcome(null);
        }}
      />

      <p className="text-ink-muted">{t('conversation.no_free_text_note')}</p>

      {notice !== null && (
        <div className="space-y-2 overflow-hidden rounded-card">
          <Banner tone={notice.tone} icon="alert">
            {t(notice.key)}
          </Banner>
          {outcome === 'rejected' && (
            <Button variant="ghost" onClick={discard}>
              {t('conversation.discard')}
            </Button>
          )}
        </div>
      )}

      <div className="sticky bottom-18 z-10 rounded-card bg-canvas/95 py-2">
        <Button icon="check" data-primary-action className="w-full" disabled={!canConfirm} busy={mutation.isPending} onClick={confirm}>
          {mutation.isPending
            ? t('conversation.sending')
            : outcome !== null && RETRY_SAME.has(outcome)
              ? t('conversation.retry')
              : t('conversation.confirm')}
        </Button>
      </div>
    </div>
  );
}

function ConversationView({ familyId }: { readonly familyId: string }) {
  const names = useLocalNames();
  const ficha = useFamilia(familyId);
  // Checklist: todas las oportunidades en el orden `prioridad` de C3 (independiente de `?orden`).
  const prioridad = useOportunidades(familyId, 'prioridad', ficha.isSuccess);

  let body;
  if (ficha.isPending) {
    body = <Skeleton rows={3} rowClass="h-16" />;
  } else if (ficha.isError && ficha.data === undefined) {
    body = <ErrorState error={ficha.error} onRetry={() => void ficha.refetch()} />;
  } else {
    const detail = ficha.data.body.data;
    const options = prioridad.data?.body.items ?? detail.top_opportunities;
    body =
      detail.top_opportunities.length === 0 ? (
        <EmptyState message={t('conversation.no_benefits')} />
      ) : (
        <>
          <DataFreshness result={ficha.data} />
          <ConversationForm detail={detail} snapshotId={ficha.data.body.meta.snapshot_id} options={options} />
        </>
      );
  }

  return (
    <div className="space-y-4">
      <ButtonLink to={familyRoutes.ficha(familyId)} variant="ghost" icon="chevron-left" className="-ml-3">
        {t('nav.back')}
      </ButtonLink>
      <PageTitle>{t('conversation.title')}</PageTitle>
      {/* Nombre de trato local (DEC-038): solo se muestra; el request lleva solo IDs y enums. */}
      <p className="font-semibold">{familyDisplayName(familyId, names)}</p>
      {body}
    </div>
  );
}

export default function ConversationPage() {
  const { familyId } = useParams();
  if (!isValidId(familyId)) return <NotFoundPage />;
  return <ConversationView key={familyId} familyId={familyId} />;
}
