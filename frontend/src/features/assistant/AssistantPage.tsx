// Chat de situaciones (design.md §9.8; plan de arreglos, Tarea 4 y §7). La tía cuenta qué pasa con una
// familia y el asistente muestra apoyos del catálogo; NO decide elegibilidad individual. Intents de C3:
// CATALOG_INFO → texto + citas HTTPS tipadas; REQUIRES_DETERMINISTIC_EVALUATION → derivar a la ficha
// SIN mostrar `answer`. Si la API falla, plantilla fija del catálogo i18n (nunca texto inventado).
// Las preguntas del jardín se responden aquí con plantilla desde `GET /kpi` (sin /asistente ni LLM).
// RUT/teléfono/correo y los nombres guardados en el equipo (DEC-038) no se envían. El historial vive
// solo en memoria.
import { useEffect, useId, useRef, useState } from 'react';
import type { AssistantEnvelope } from '../../api/types';
import { useAskAssistant } from '../../data/mutations';
import { useKpi } from '../../data/queries';
import { errorCopyKey, helpCodeOf } from '../../domain/errorCopy';
import { formatInteger } from '../../domain/format';
import { containsPii } from '../../domain/piiGuard';
import { t } from '../../i18n/copy';
import { containsLocalName, useLocalNames } from '../../offline/localNames';
import { Button, ButtonLink } from '../../ui/Button';
import { ProviderNote } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { ReferentialNotice } from '../../ui/states';
import { SourceLink } from '../../ui/SourceLink';
import { DEMO_COPY, GARDEN_EXAMPLES, SITUATION_EXAMPLES, type GardenQuestionKind } from '../demo-session/demoCopy';
import { useSelectedGarden } from '../system/useSelectedGarden';
import { gardenAnswer } from './gardenAnswers';


const MAX_CHARS = 500;
/** Code points (no unidades UTF-16), como cuenta C3 `maxLength`. */
const codePoints = (text: string): number => [...text].length;

type ChatTurn =
  | { readonly id: number; readonly kind: 'user'; readonly text: string }
  | { readonly id: number; readonly kind: 'pending' }
  | { readonly id: number; readonly kind: 'answer'; readonly envelope: AssistantEnvelope }
  | { readonly id: number; readonly kind: 'local'; readonly text: string }
  | { readonly id: number; readonly kind: 'pii' }
  | { readonly id: number; readonly kind: 'error'; readonly error: unknown; readonly question: string };

const BUBBLE_ASSISTANT = 'mr-6 space-y-3 rounded-card rounded-tl-sm border border-border bg-surface p-4 shadow-sm';

function AnswerBubble({ envelope }: { readonly envelope: AssistantEnvelope }) {
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
function TemplateFallback({ error, onRetry }: { readonly error: unknown; readonly onRetry: () => void }) {
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

function Turn({ turn, onRetry }: { readonly turn: ChatTurn; readonly onRetry: (question: string) => void }) {
  switch (turn.kind) {
    case 'user':
      return (
        <div className="ml-6 rounded-card rounded-tr-sm bg-primary p-4 text-surface">
          <p className="sr-only">{DEMO_COPY.chatYou}:</p>
          <p className="whitespace-pre-line">{turn.text}</p>
        </div>
      );
    case 'pending':
      return (
        <p role="status" className={`${BUBBLE_ASSISTANT} text-ink-muted`}>
          {t('assistant.thinking')}
        </p>
      );
    case 'answer':
      return <AnswerBubble envelope={turn.envelope} />;
    case 'local':
      return (
        <div className={BUBBLE_ASSISTANT}>
          <p>{turn.text}</p>
          <ReferentialNotice />
        </div>
      );
    case 'pii':
      return (
        <div className={BUBBLE_ASSISTANT}>
          <p role="alert" className="font-semibold">
            {t('assistant.pii_blocked')}
          </p>
        </div>
      );
    case 'error':
      return <TemplateFallback error={turn.error} onRetry={() => onRetry(turn.question)} />;
  }
}

export default function AssistantPage() {
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<readonly ChatTurn[]>([]);
  const [nameBlocked, setNameBlocked] = useState(false);
  const names = useLocalNames();
  const ask = useAskAssistant();
  const { garden } = useSelectedGarden();
  const kpi = useKpi(garden !== undefined ? { nivel: 'jardin', id: garden.garden_id } : null);
  const fieldId = useId();
  const counterId = useId();
  const nextId = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);
  const trimmed = question.trim();

  useEffect(() => {
    if (turns.length > 0) endRef.current?.scrollIntoView?.({ block: 'end' });
  }, [turns]);

  const id = () => (nextId.current += 1);
  const push = (...next: ChatTurn[]) => setTurns((prev) => [...prev, ...next]);
  const replacePending = (pendingId: number, turn: ChatTurn) =>
    setTurns((prev) => prev.map((item) => (item.id === pendingId ? turn : item)));

  const send = (text: string, showUser = true) => {
    const clean = text.trim();
    if (clean === '' || codePoints(clean) > MAX_CHARS || ask.isPending) return;
    if (containsPii(clean)) {
      // No se envía nada: respuesta amable local.
      push(...(showUser ? [{ id: id(), kind: 'user', text: clean } as const] : []), { id: id(), kind: 'pii' });
      setQuestion('');
      return;
    }
    // DEC-038: un nombre de trato guardado en este equipo nunca sale hacia la API.
    if (containsLocalName(clean, names)) {
      setNameBlocked(true);
      return;
    }
    setNameBlocked(false);
    const pendingId = id();
    push(...(showUser ? [{ id: id(), kind: 'user', text: clean } as const] : []), { id: pendingId, kind: 'pending' });
    setQuestion('');
    ask.mutate(clean, {
      onSuccess: (ok) => replacePending(pendingId, { id: pendingId, kind: 'answer', envelope: ok.body }),
      onError: (error) => replacePending(pendingId, { id: pendingId, kind: 'error', error, question: clean }),
    });
  };

  const askGarden = (kind: GardenQuestionKind, text: string) => {
    push({ id: id(), kind: 'user', text }, { id: id(), kind: 'local', text: gardenAnswer(kind, kpi.data?.body.data) });
  };

  return (
    <div className="space-y-5">
      <PageTitle>{DEMO_COPY.chatTitle}</PageTitle>
      <p>{DEMO_COPY.chatIntro}</p>
      <section aria-labelledby="assistant-situations" className="space-y-2">
        <h2 id="assistant-situations">{DEMO_COPY.chatSituationsTitle}</h2>
        <div className="flex flex-wrap gap-2">
          {SITUATION_EXAMPLES.map((text) => (
            <Button key={text} variant="secondary" size="sm" className="px-3 text-left" disabled={ask.isPending} onClick={() => send(text)}>
              {text}
            </Button>
          ))}
        </div>
      </section>
      <section aria-labelledby="assistant-garden" className="space-y-2">
        <h2 id="assistant-garden">{DEMO_COPY.chatGardenTitle}</h2>
        <div className="flex flex-wrap gap-2">
          {GARDEN_EXAMPLES.map((example) => (
            <Button key={example.kind} variant="secondary" size="sm" className="px-3 text-left" onClick={() => askGarden(example.kind, example.text)}>
              {example.text}
            </Button>
          ))}
        </div>
      </section>
      {turns.length > 0 && (
        <section aria-label={DEMO_COPY.chatHistoryLabel} aria-live="polite" className="space-y-3">
          {turns.map((turn) => (
            <Turn key={turn.id} turn={turn} onRetry={(q) => send(q, false)} />
          ))}
          <div ref={endRef} />
        </section>
      )}
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          send(trimmed);
        }}
      >
        <label htmlFor={fieldId} className="block font-semibold">
          {t('assistant.question_label')}
        </label>
        <textarea
          id={fieldId}
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
            setNameBlocked(false);
          }}
          maxLength={MAX_CHARS}
          rows={3}
          aria-describedby={counterId}
          aria-invalid={nameBlocked || undefined}
          className="w-full rounded-xl border-2 border-border-strong bg-surface p-3"
        />
        <p id={counterId} className="text-[0.9rem] text-ink-muted">
          {t('assistant.char_count', { count: formatInteger(codePoints(question)), max: formatInteger(MAX_CHARS) })}
        </p>
        {nameBlocked && (
          <p role="alert" className="font-semibold text-danger-ink">
            {t('assistant.name_blocked')}
          </p>
        )}
        <Button type="submit" icon="chat" data-primary-action className="w-full" disabled={trimmed === ''} busy={ask.isPending}>
          {t('assistant.submit')}
        </Button>
      </form>
    </div>
  );
}
