// Burbujas del chat, compartidas por el chat de situaciones (AssistantPage) y el chat de la ficha
// (FamilyChat): tía a la derecha, agente a la izquierda. CATALOG_INFO → texto + citas HTTPS tipadas;
// REQUIRES_DETERMINISTIC_EVALUATION → derivar SIN mostrar `answer`. Ante falla, plantilla fija.
// El aviso referencial NO va en cada burbuja: cada vista lo muestra una sola vez al pie (ChatNotice) y
// el literal se recorta del `answer` al mostrar (C3 sigue enviándolo).
import type { AssistantEnvelope } from '../../api/types';
import { errorCopyKey, helpCodeOf } from '../../domain/errorCopy';
import { t } from '../../i18n/copy';
import { Button, ButtonLink } from '../../ui/Button';
import { ProviderNote } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { SourceLink } from '../../ui/SourceLink';
import { DEMO_COPY } from '../demo-session/demoCopy';
import { stripDisclaimer } from './chatContext';

export const BUBBLE_ASSISTANT = 'mr-6 space-y-3 rounded-card rounded-tl-sm border border-border bg-surface p-4 shadow-sm';
const BUBBLE_USER = 'ml-6 rounded-card rounded-tr-sm bg-primary p-4 text-surface';

/** Lo que escribió la tía, tal cual (vive solo en memoria de este equipo). */
export function UserBubble({ text }: { readonly text: string }) {
  return (
    <div className={BUBBLE_USER}>
      <p className="sr-only">{DEMO_COPY.chatYou}:</p>
      <p className="whitespace-pre-line">{text}</p>
    </div>
  );
}

/** Indicador "escribiendo…" mientras llega la respuesta. */
export function TypingBubble() {
  return (
    <p role="status" className={`${BUBBLE_ASSISTANT} flex w-fit items-center gap-2 text-ink-muted`}>
      <span aria-hidden="true" className="flex gap-1">
        {[0, 150, 300].map((delay) => (
          <span key={delay} className="size-2 rounded-full bg-ink-muted motion-safe:animate-bounce" style={{ animationDelay: `${delay}ms` }} />
        ))}
      </span>
      {DEMO_COPY.chatTyping}
    </p>
  );
}

export function AnswerBubble({ envelope }: { readonly envelope: AssistantEnvelope }) {
  if (envelope.intent === 'REQUIRES_DETERMINISTIC_EVALUATION') {
    return (
      <div className={BUBBLE_ASSISTANT}>
        <p className="font-semibold">{t('assistant.deterministic_redirect')}</p>
        <ButtonLink to="/" icon="home" className="w-full">
          {t('assistant.go_home')}
        </ButtonLink>
      </div>
    );
  }
  return (
    <div className={BUBBLE_ASSISTANT}>
      <h3 className="sr-only">{t('assistant.answer_title')}</h3>
      <ProviderNote provider={envelope.provider} warnings={envelope.warnings} />
      <p className="c3-text whitespace-pre-line">{stripDisclaimer(envelope.answer)}</p>
      {envelope.citations.length > 0 && (
        <div>
          <h3 className="text-base">{t('assistant.citations_title')}</h3>
          <ul>
            {envelope.citations.map((citation) => (
              <li key={citation.source_id}>
                <SourceLink citation={citation} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Plantilla fija ante falla o sin respuesta: solo claves del catálogo, sin contenido del servidor. */
export function TemplateFallback({ error, onRetry }: { readonly error: unknown; readonly onRetry: () => void }) {
  const helpCode = helpCodeOf(error);
  return (
    <div className={BUBBLE_ASSISTANT}>
      <ProviderNote provider="PLANTILLA" warnings={[]} />
      <p role="alert" className="flex items-start gap-2 font-semibold text-danger-ink">
        <Icon name="alert" className="mt-0.5 size-5" />
        {t(errorCopyKey(error))}
      </p>
      {helpCode !== null && <p className="text-sm">{t('error.help_code', { request_id: helpCode })}</p>}
      <p>{t('card.where_none')}</p>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" icon="refresh" onClick={onRetry}>
          {t('common.retry')}
        </Button>
        <ButtonLink to="/" variant="ghost" icon="home">
          {t('assistant.go_home')}
        </ButtonLink>
      </div>
    </div>
  );
}

/** El aviso referencial, una sola vez y discreto, al pie de la vista del chat. */
export function ChatNotice() {
  return (
    <p role="note" data-chat-notice className="flex items-start gap-1.5 text-[0.85rem] text-ink-muted">
      <Icon name="info" className="mt-0.5 size-4 shrink-0" />
      <span>{t('notice.referential')}</span>
    </p>
  );
}
