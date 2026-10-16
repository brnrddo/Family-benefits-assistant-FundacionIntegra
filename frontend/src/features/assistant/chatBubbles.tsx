// Burbujas de respuesta del asistente, compartidas por el chat de situaciones (AssistantPage) y el
// chat de la ficha (FamilyChat). CATALOG_INFO → texto + citas HTTPS tipadas y aviso;
// REQUIRES_DETERMINISTIC_EVALUATION → derivar SIN mostrar `answer`. Ante falla, plantilla fija.
import type { AssistantEnvelope } from '../../api/types';
import { errorCopyKey, helpCodeOf } from '../../domain/errorCopy';
import { t } from '../../i18n/copy';
import { Button, ButtonLink } from '../../ui/Button';
import { ProviderNote } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { ReferentialNotice } from '../../ui/states';
import { SourceLink } from '../../ui/SourceLink';

export const BUBBLE_ASSISTANT = 'mr-6 space-y-3 rounded-card rounded-tl-sm border border-border bg-surface p-4 shadow-sm';

export function AnswerBubble({ envelope }: { readonly envelope: AssistantEnvelope }) {
  if (envelope.intent === 'REQUIRES_DETERMINISTIC_EVALUATION') {
    return (
      <div className={BUBBLE_ASSISTANT}>
        <p className="font-semibold">{t('assistant.deterministic_redirect')}</p>
        <ButtonLink to="/" icon="home" className="w-full">
          {t('assistant.go_home')}
        </ButtonLink>
        <ReferentialNotice />
      </div>
    );
  }
  return (
    <div className={BUBBLE_ASSISTANT}>
      <h3 className="sr-only">{t('assistant.answer_title')}</h3>
      <ProviderNote provider={envelope.provider} warnings={envelope.warnings} />
      <p className="c3-text whitespace-pre-line">{envelope.answer}</p>
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
      <ReferentialNotice />
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
      <ReferentialNotice />
    </div>
  );
}
