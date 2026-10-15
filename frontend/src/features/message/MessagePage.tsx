// Mensaje e impresión (design.md §9.5, FE-008/FE-009): vista previa de WhatsApp SOLO para copiar
// (sin wa.me ni envío) y tarjeta CARD_V1 con "Imprimir". Todo texto de C3 se muestra como texto.
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router';
import { useFamilia, useMensaje } from '../../data/queries';
import { isValidId } from '../../domain/ids';
import { t } from '../../i18n/copy';
import { Button, ButtonLink } from '../../ui/Button';
import { ProviderNote } from '../../ui/DataStatus';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { toastStore } from '../../ui/toastStore';
import { familyRoutes } from '../family/routes';
import NotFoundPage from '../system/NotFoundPage';
import { PrintableCardV1 } from './PrintableCardV1';

function CopyBlock({ text }: { readonly text: string }) {
  const [failed, setFailed] = useState(false);
  const fallbackRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (failed) fallbackRef.current?.select();
  }, [failed]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setFailed(false);
      toastStore.push(t('message.copied'));
    } catch {
      setFailed(true);
    }
  };

  return (
    <div className="space-y-3">
      <Button icon="copy" data-primary-action className="w-full" onClick={() => void copy()}>
        {t('message.copy')}
      </Button>
      {failed && (
        <>
          <p role="alert" className="text-danger-ink">
            {t('message.copy_failed')}
          </p>
          <textarea
            ref={fallbackRef}
            readOnly
            value={text}
            aria-label={t('message.whatsapp_title')}
            rows={6}
            className="c3-text w-full rounded-xl border border-border-strong p-3"
          />
        </>
      )}
    </div>
  );
}

function MessageView({ familyId }: { readonly familyId: string }) {
  const ficha = useFamilia(familyId);
  const benefitIds = ficha.data?.body.data.top_opportunities.map((o) => o.benefit_id) ?? [];
  const mensaje = useMensaje(familyId, benefitIds);

  let body;
  if (ficha.isPending || (benefitIds.length > 0 && mensaje.isPending)) {
    body = (
      <>
        <p className="text-ink-muted">{t('message.generating')}</p>
        <Skeleton rows={2} rowClass="h-40" />
      </>
    );
  } else if (ficha.isError && ficha.data === undefined) {
    body = <ErrorState error={ficha.error} onRetry={() => void ficha.refetch()} />;
  } else if (benefitIds.length === 0) {
    body = <EmptyState message={t('empty.opportunities')} />;
  } else if (mensaje.isError) {
    body = <ErrorState error={mensaje.error} onRetry={() => void mensaje.refetch()} />;
  } else if (mensaje.data !== undefined) {
    const envelope = mensaje.data.body;
    body = (
      <>
        <div data-print-hide className="space-y-4">
          <ProviderNote provider={envelope.provider} warnings={envelope.warnings} />
          <section aria-labelledby="message-preview" className="space-y-3">
            <h2 id="message-preview">{t('message.whatsapp_title')}</h2>
            <p className="text-ink-muted">{t('message.whatsapp_hint')}</p>
            <div className="c3-text whitespace-pre-line rounded-card border border-go-icon bg-go-bg p-4 text-go-ink">
              {envelope.content.whatsapp_preview}
            </div>
            <CopyBlock text={envelope.content.whatsapp_preview} />
          </section>
        </div>
        <section aria-labelledby="message-card" className="space-y-3">
          <h2 id="message-card" data-print-hide>
            {t('message.card_title')}
          </h2>
          <PrintableCardV1 card={envelope.content.printable_card} />
          <Button variant="secondary" icon="print" className="w-full" data-print-hide onClick={() => window.print()}>
            {t('message.print')}
          </Button>
        </section>
        <div data-print-hide>
          <ReferentialNotice />
        </div>
      </>
    );
  }

  return (
    <div className="space-y-4">
      <div data-print-hide>
        <ButtonLink to={familyRoutes.ficha(familyId)} variant="ghost" icon="chevron-left" className="-ml-3">
          {t('nav.back')}
        </ButtonLink>
      </div>
      <PageTitle>{t('message.title')}</PageTitle>
      {body}
    </div>
  );
}

export default function MessagePage() {
  const { familyId } = useParams();
  if (!isValidId(familyId)) return <NotFoundPage />;
  return <MessageView key={familyId} familyId={familyId} />;
}
