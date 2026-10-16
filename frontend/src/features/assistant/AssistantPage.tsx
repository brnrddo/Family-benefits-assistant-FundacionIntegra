// Chat de situaciones (design.md §9.8; plan de arreglos, Tarea 4 y §7). La tía cuenta qué pasa con una
// familia y el asistente muestra apoyos del catálogo; NO decide elegibilidad individual. Intents de C3:
// CATALOG_INFO → texto + citas HTTPS tipadas; REQUIRES_DETERMINISTIC_EVALUATION → derivar a la ficha
// SIN mostrar `answer`. Si la API falla, plantilla fija del catálogo i18n (nunca texto inventado).
// Las preguntas del jardín se responden aquí con plantilla desde `GET /kpi` (sin /asistente ni LLM).
// RUT/teléfono/correo no se envían. Los nombres guardados en el equipo y los apellidos del directorio
// demo se cambian por "el niño o la niña" / "la familia" antes de enviar (DEC-038: nunca salen); el
// historial muestra lo que escribió la tía y vive solo en memoria. Cada envío lleva un resumen corto
// de la respuesta anterior para dar continuidad (chatContext.ts). Aviso referencial una vez, al pie.
import { useEffect, useId, useRef, useState } from 'react';
import type { AssistantEnvelope } from '../../api/types';
import { useAskAssistant } from '../../data/mutations';
import { useFamilias, useKpi } from '../../data/queries';
import { formatInteger } from '../../domain/format';
import { containsPii } from '../../domain/piiGuard';
import { t } from '../../i18n/copy';
import { containsLocalName, useLocalNames } from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { PageTitle } from '../../ui/PageTitle';
import { DEMO_COPY, GARDEN_EXAMPLES, SITUATION_EXAMPLES, type GardenQuestionKind } from '../demo-session/demoCopy';
import { useDemoDirectory } from '../demo-session/session';
import { memoryGreeting, useDayPlan } from '../home/todayAction';
import { useSelectedGarden } from '../system/useSelectedGarden';
import { AnswerBubble, BUBBLE_ASSISTANT, ChatNotice, TemplateFallback, TypingBubble, UserBubble } from './chatBubbles';
import { anonymize, codePoints, composeGeneralQuestion, lastAnswerOf } from './chatContext';
import { gardenAnswer } from './gardenAnswers';

const MAX_CHARS = 500;

type ChatTurn =
  | { readonly id: number; readonly kind: 'user'; readonly text: string }
  | { readonly id: number; readonly kind: 'pending' }
  | { readonly id: number; readonly kind: 'answer'; readonly envelope: AssistantEnvelope }
  | { readonly id: number; readonly kind: 'local'; readonly text: string }
  | { readonly id: number; readonly kind: 'pii' }
  | { readonly id: number; readonly kind: 'error'; readonly error: unknown; readonly question: string };

function Turn({ turn, onRetry }: { readonly turn: ChatTurn; readonly onRetry: (question: string) => void }) {
  switch (turn.kind) {
    case 'user':
      return <UserBubble text={turn.text} />;
    case 'pending':
      return <TypingBubble />;
    case 'answer':
      return <AnswerBubble envelope={turn.envelope} />;
    case 'local':
      return (
        <div className={BUBBLE_ASSISTANT}>
          <p>{turn.text}</p>
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
  const directory = useDemoDirectory();
  const ask = useAskAssistant();
  const { garden } = useSelectedGarden();
  const kpi = useKpi(garden !== undefined ? { nivel: 'jardin', id: garden.garden_id } : null);
  // DEC-091: saludo con memoria local (lo último hecho y la acción de hoy). Texto local, nunca se envía.
  const familias = useFamilias(garden?.garden_id);
  const plan = useDayPlan(familias.data?.pages.flatMap((page) => page.body.items) ?? []);
  const memory = familias.data === undefined ? null : memoryGreeting(plan);
  const fieldId = useId();
  const counterId = useId();
  const hintId = useId();
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

  const request = (outgoing: string, pendingId: number) => {
    ask.mutate(outgoing, {
      onSuccess: (ok) => replacePending(pendingId, { id: pendingId, kind: 'answer', envelope: ok.body }),
      onError: (error) => replacePending(pendingId, { id: pendingId, kind: 'error', error, question: outgoing }),
    });
  };

  const send = (text: string) => {
    const clean = text.trim();
    if (clean === '' || codePoints(clean) > MAX_CHARS || ask.isPending) return;
    if (containsPii(clean)) {
      // No se envía nada: respuesta amable local.
      push({ id: id(), kind: 'user', text: clean }, { id: id(), kind: 'pii' });
      setQuestion('');
      return;
    }
    // DEC-038: los nombres se cambian por "el niño o la niña" / "la familia" (también en el resumen
    // del turno anterior); lo que ve la tía en pantalla sigue con el nombre.
    const previous = lastAnswerOf(turns);
    const outgoing = composeGeneralQuestion(
      anonymize(clean, names, directory),
      previous === null ? null : anonymize(previous, names, directory),
    );
    // Defensa final: si algún nombre guardado sobrevivió, no se envía nada.
    if (containsLocalName(outgoing, names)) {
      setNameBlocked(true);
      return;
    }
    setNameBlocked(false);
    const pendingId = id();
    push({ id: id(), kind: 'user', text: clean }, { id: pendingId, kind: 'pending' });
    setQuestion('');
    request(outgoing, pendingId);
  };

  const retry = (outgoing: string) => {
    if (ask.isPending) return;
    const pendingId = id();
    push({ id: pendingId, kind: 'pending' });
    request(outgoing, pendingId);
  };

  const askGarden = (kind: GardenQuestionKind, text: string) => {
    push({ id: id(), kind: 'user', text }, { id: id(), kind: 'local', text: gardenAnswer(kind, kpi.data?.body.data) });
  };

  return (
    <div className="space-y-5 lg:mx-auto lg:max-w-3xl">
      <PageTitle>{DEMO_COPY.chatTitle}</PageTitle>
      <p>{DEMO_COPY.chatIntro}</p>
      {memory !== null && (
        <div data-chat-memory className={BUBBLE_ASSISTANT}>
          <p className="sr-only">{DEMO_COPY.chatAssistant}:</p>
          <p>{memory}</p>
        </div>
      )}
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
        <section aria-label={DEMO_COPY.chatHistoryLabel} role="log" aria-live="polite" className="space-y-3">
          {turns.map((turn) => (
            <Turn key={turn.id} turn={turn} onRetry={retry} />
          ))}
          <div ref={endRef} />
        </section>
      )}
      {/* Entrada fija abajo, sobre la barra de navegación (móvil) o al pie de la ventana (escritorio). */}
      <form
        data-chat-input
        className="sticky bottom-18 z-10 space-y-2 border-t border-border bg-canvas/95 pb-2 pt-3 lg:bottom-0"
        onSubmit={(event) => {
          event.preventDefault();
          send(trimmed);
        }}
      >
        <label htmlFor={fieldId} className="block font-semibold">
          {t('assistant.question_label')}
        </label>
        <p id={hintId} className="text-[0.9rem] text-ink-muted">
          {DEMO_COPY.chatNamesHint}
        </p>
        <div className="flex items-end gap-2">
          <textarea
            id={fieldId}
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value);
              setNameBlocked(false);
            }}
            onKeyDown={(event) => {
              // Enter envía; Mayús+Enter agrega una línea (como un chat).
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                send(trimmed);
              }
            }}
            maxLength={MAX_CHARS}
            rows={2}
            aria-describedby={`${hintId} ${counterId}`}
            aria-invalid={nameBlocked || undefined}
            className="min-w-0 flex-1 rounded-xl border-2 border-border-strong bg-surface p-3"
          />
          <Button type="submit" icon="chat" data-primary-action disabled={trimmed === ''} busy={ask.isPending}>
            {t('assistant.submit')}
          </Button>
        </div>
        <p id={counterId} className="text-[0.9rem] text-ink-muted">
          {t('assistant.char_count', { count: formatInteger(codePoints(question)), max: formatInteger(MAX_CHARS) })}
        </p>
        {nameBlocked && (
          <p role="alert" className="font-semibold text-danger-ink">
            {t('assistant.name_blocked')}
          </p>
        )}
      </form>
      <ChatNotice />
    </div>
  );
}
