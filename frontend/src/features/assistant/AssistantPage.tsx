// Asistente de catálogo (design.md §9.8, FE-001/FE-004/FE-005). Solo preguntas generales: el
// asistente NO decide elegibilidad individual. Intents de C3: CATALOG_INFO → respuesta como texto +
// citas HTTPS tipadas; REQUIRES_DETERMINISTIC_EVALUATION → derivar a la ficha SIN mostrar `answer`.
// Si la API falla o no responde, se muestra una plantilla fija del catálogo i18n (nunca texto
// inventado). La barrera local bloquea RUT/teléfono/correo sin enviar; no anonimiza (el servidor
// aplica su filtro y Guardrails). Pregunta y respuesta solo viven en memoria.
import { useId, useState } from 'react';
import type { AssistantEnvelope } from '../../api/types';
import { useAskAssistant } from '../../data/mutations';
import { containsPii } from '../../domain/piiGuard';
import { errorCopyKey, helpCodeOf } from '../../domain/errorCopy';
import { formatInteger } from '../../domain/format';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { Button, ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ProviderNote } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { ReferentialNotice } from '../../ui/states';
import { SourceLink } from '../../ui/SourceLink';

const MAX_CHARS = 500;
const EXAMPLES: readonly PlainCopyKey[] = ['assistant.example.1', 'assistant.example.2', 'assistant.example.3'];

/** Code points (no unidades UTF-16), como cuenta C3 `maxLength`. */
const codePoints = (text: string): number => [...text].length;

function Answer({ envelope }: { readonly envelope: AssistantEnvelope }) {
  if (envelope.intent === 'REQUIRES_DETERMINISTIC_EVALUATION') {
    return (
      <Card className="space-y-3">
        <p className="font-semibold">{t('assistant.deterministic_redirect')}</p>
        <ButtonLink to="/" icon="home" className="w-full">
          {t('assistant.go_home')}
        </ButtonLink>
        <ReferentialNotice />
      </Card>
    );
  }
  return (
    <Card className="space-y-3">
      <h2>{t('assistant.answer_title')}</h2>
      <ProviderNote provider={envelope.provider} warnings={envelope.warnings} />
      <p className="c3-text whitespace-pre-line">{envelope.answer}</p>
      {envelope.citations.length > 0 && (
        <div>
          <h3>{t('assistant.citations_title')}</h3>
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
    </Card>
  );
}

/** Plantilla fija ante falla o sin respuesta: solo claves del catálogo, sin contenido del servidor. */
function TemplateFallback({ error, onRetry }: { readonly error: unknown; readonly onRetry: () => void }) {
  const helpCode = helpCodeOf(error);
  return (
    <Card className="space-y-3">
      <h2>{t('assistant.answer_title')}</h2>
      <ProviderNote provider="PLANTILLA" warnings={[]} />
      <p role="alert" className="flex items-start gap-2 font-semibold text-danger-ink">
        <Icon name="alert" className="mt-0.5 size-5" />
        {t(errorCopyKey(error))}
      </p>
      {helpCode !== null && <p className="text-sm">{t('error.help_code', { request_id: helpCode })}</p>}
      <p>{t('assistant.intro')}</p>
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
    </Card>
  );
}

export default function AssistantPage() {
  const [question, setQuestion] = useState('');
  const [piiBlocked, setPiiBlocked] = useState(false);
  const ask = useAskAssistant();
  const fieldId = useId();
  const hintId = useId();
  const counterId = useId();
  const trimmed = question.trim();

  const submit = () => {
    if (trimmed === '' || codePoints(trimmed) > MAX_CHARS) return;
    if (containsPii(trimmed)) {
      setPiiBlocked(true); // falla cerrada: no se envía nada
      ask.reset();
      return;
    }
    setPiiBlocked(false);
    ask.mutate(trimmed);
  };

  const edit = (value: string) => {
    setQuestion(value);
    setPiiBlocked(false);
  };

  return (
    <div className="space-y-5">
      <PageTitle>{t('assistant.title')}</PageTitle>
      <p>{t('assistant.intro')}</p>

      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label htmlFor={fieldId} className="block font-semibold">
          {t('assistant.question_label')} {t('a11y.required')}
        </label>
        <p id={hintId} className="text-ink-muted">
          {t('notice.no_sensitive_data')}
        </p>
        <textarea
          id={fieldId}
          value={question}
          onChange={(event) => edit(event.target.value)}
          maxLength={MAX_CHARS}
          required
          rows={4}
          aria-describedby={`${hintId} ${counterId}`}
          aria-invalid={piiBlocked || undefined}
          className="w-full rounded-xl border-2 border-border-strong bg-surface p-3"
        />
        <p id={counterId} className="text-[0.9rem] text-ink-muted">
          {t('assistant.char_count', { count: formatInteger(codePoints(question)), max: formatInteger(MAX_CHARS) })}
        </p>
        {piiBlocked && (
          <p role="alert" className="font-semibold text-danger-ink">
            {t('assistant.pii_blocked')}
          </p>
        )}
        <Button type="submit" icon="chat" data-primary-action className="w-full" disabled={trimmed === ''} busy={ask.isPending}>
          {ask.isPending ? t('assistant.thinking') : t('assistant.submit')}
        </Button>
      </form>

      <section aria-labelledby="assistant-examples" className="space-y-2">
        <h2 id="assistant-examples">{t('assistant.examples_title')}</h2>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((key) => (
            <Button key={key} variant="secondary" className="w-full justify-start text-left" onClick={() => edit(t(key))}>
              {t(key)}
            </Button>
          ))}
        </div>
      </section>

      {ask.isPending && (
        <p role="status" className="text-ink-muted">
          {t('assistant.thinking')}
        </p>
      )}
      {ask.isError && <TemplateFallback error={ask.error} onRetry={submit} />}
      {ask.isSuccess && <Answer envelope={ask.data.body} />}
      <p className="text-[0.9rem] text-ink-muted">{t('assistant.not_saved')}</p>
    </div>
  );
}
