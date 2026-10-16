// Chat de la ficha (guion de demo 2026-10-16): la tía cuenta la situación de ESTA familia y el
// asistente propone 1–3 acciones. Se monta dentro de FamilyQuickQuestions (FamilyPage no cambia).
// El hilo vive solo en memoria (useState, no se persiste). Antes de enviar: RUT/teléfono/correo →
// no se envía; los nombres guardados en el equipo y los apellidos del directorio demo se cambian por
// "el niño o la niña" / "la familia" (DEC-038: nunca salen); si aun así queda un nombre, falla
// cerrada. El contexto sale de lo que la ficha ya cargó (misma caché de GET /familias/{id} y
// /oportunidades) y solo lleva datos permitidos (roles/edades, tramo RSH, títulos y estado).
import { useId, useRef, useState } from 'react';
import type { AssistantEnvelope } from '../../api/types';
import { useAskAssistant } from '../../data/mutations';
import { useFamilia, useOportunidades } from '../../data/queries';
import { containsPii } from '../../domain/piiGuard';
import { t } from '../../i18n/copy';
import { containsLocalName, replaceLocalNames, useLocalNames } from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { DEMO_COPY } from '../demo-session/demoCopy';
import { useDemoDirectory } from '../demo-session/session';
import { AnswerBubble, BUBBLE_ASSISTANT, TemplateFallback } from './chatBubbles';
import { composeFamilyQuestion, TIA_TEXT_MAX } from './familyChatQuestion';

type Turn =
  | { readonly id: number; readonly kind: 'user'; readonly text: string }
  | { readonly id: number; readonly kind: 'pending' }
  | { readonly id: number; readonly kind: 'answer'; readonly envelope: AssistantEnvelope }
  | { readonly id: number; readonly kind: 'pii' }
  | { readonly id: number; readonly kind: 'error'; readonly error: unknown; readonly question: string };

/** Apellidos del directorio demo ("Familia Rojas Muñoz" → ["Rojas Muñoz"]), para sustituirlos. */
const familyWords = (familyName: string | undefined): string[] =>
  familyName === undefined ? [] : [familyName.replace(/^familia\s+/iu, '')];

export function FamilyChat({ familyId }: { readonly familyId: string }) {
  const familia = useFamilia(familyId);
  const oportunidades = useOportunidades(familyId, 'prioridad');
  const names = useLocalNames();
  const directory = useDemoDirectory();
  const ask = useAskAssistant();
  const [text, setText] = useState('');
  const [turns, setTurns] = useState<readonly Turn[]>([]);
  const [nameBlocked, setNameBlocked] = useState(false);
  const fieldId = useId();
  const hintId = useId();
  const nextId = useRef(0);
  const detail = familia.data?.body.data;
  const trimmed = text.trim();

  const id = () => (nextId.current += 1);
  const replacePending = (pendingId: number, turn: Turn) => setTurns((prev) => prev.map((item) => (item.id === pendingId ? turn : item)));

  const sendQuestion = (question: string) => {
    const pendingId = id();
    setTurns((prev) => [...prev, { id: pendingId, kind: 'pending' }]);
    ask.mutate(question, {
      onSuccess: (ok) => replacePending(pendingId, { id: pendingId, kind: 'answer', envelope: ok.body }),
      onError: (error) => replacePending(pendingId, { id: pendingId, kind: 'error', error, question }),
    });
  };

  const send = () => {
    if (trimmed === '' || detail === undefined || ask.isPending) return;
    if (containsPii(trimmed)) {
      setTurns((prev) => [...prev, { id: id(), kind: 'pii' }]);
      setText('');
      return;
    }
    const tiaText = replaceLocalNames(trimmed, names, familyWords(directory.get(familyId)?.familyName));
    const question = composeFamilyQuestion({
      composition: detail.composition,
      rshBand: detail.rsh_band,
      opportunities: oportunidades.data?.body.items ?? detail.top_opportunities,
      tiaText,
    });
    // Defensa final (DEC-038): si algún nombre guardado sobrevivió, no se envía nada.
    if (containsLocalName(question, names)) {
      setNameBlocked(true);
      return;
    }
    setNameBlocked(false);
    setText('');
    setTurns((prev) => [...prev, { id: id(), kind: 'user', text: tiaText }]);
    sendQuestion(question);
  };

  return (
    <div data-family-chat className="space-y-3 border-t border-border pt-3">
      {turns.length > 0 && (
        <div aria-label={DEMO_COPY.chatHistoryLabel} role="log" aria-live="polite" className="space-y-3">
          {turns.map((turn) => {
            switch (turn.kind) {
              case 'user':
                return (
                  <div key={turn.id} className="ml-6 rounded-card rounded-tr-sm bg-primary p-4 text-surface">
                    <p className="sr-only">{DEMO_COPY.chatYou}:</p>
                    <p className="whitespace-pre-line">{turn.text}</p>
                  </div>
                );
              case 'pending':
                return (
                  <p key={turn.id} role="status" className={`${BUBBLE_ASSISTANT} text-ink-muted`}>
                    {t('assistant.thinking')}
                  </p>
                );
              case 'answer':
                return <AnswerBubble key={turn.id} envelope={turn.envelope} />;
              case 'pii':
                return (
                  <div key={turn.id} className={BUBBLE_ASSISTANT}>
                    <p role="alert" className="font-semibold">
                      {t('assistant.pii_blocked')}
                    </p>
                  </div>
                );
              case 'error':
                return <TemplateFallback key={turn.id} error={turn.error} onRetry={() => sendQuestion(turn.question)} />;
            }
          })}
        </div>
      )}
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          send();
        }}
      >
        <label htmlFor={fieldId} className="block font-semibold">
          {DEMO_COPY.familyChatLabel}
        </label>
        <p id={hintId} className="text-[0.9rem] text-ink-muted">
          {DEMO_COPY.familyChatHint}
        </p>
        <textarea
          id={fieldId}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setNameBlocked(false);
          }}
          maxLength={TIA_TEXT_MAX}
          rows={2}
          aria-describedby={hintId}
          aria-invalid={nameBlocked || undefined}
          className="w-full rounded-xl border-2 border-border-strong bg-surface p-3"
        />
        {nameBlocked && (
          <p role="alert" className="font-semibold text-danger-ink">
            {DEMO_COPY.familyChatNameBlocked}
          </p>
        )}
        <Button type="submit" icon="chat" variant="secondary" className="w-full" disabled={trimmed === '' || detail === undefined} busy={ask.isPending}>
          {DEMO_COPY.familyChatSubmit}
        </Button>
      </form>
    </div>
  );
}

export default FamilyChat;
