// "Preguntas tipo" de una familia (plan de arreglos §7, Persona B). Se exporta para que la ficha
// (features/family/FamilyPage.tsx, de Persona A) lo monte: `<FamilyQuickQuestions familyId={id} />`.
// Respuestas deterministas desde `GET /familias/{id}/oportunidades` (sin LLM ni /asistente). Debajo,
// el chat de la ficha (`FamilyChat`, guion de demo 2026-10-16): ese sí usa `POST /asistente`, con un
// contexto permitido y sin nombres.
import { useId, useState } from 'react';
import { useFamilia, useOportunidades } from '../../data/queries';
import { useLocalNames } from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ReferentialNotice, Skeleton } from '../../ui/states';
import { DEMO_COPY } from '../demo-session/demoCopy';
import { FamilyChat } from './FamilyChat';
import { firstName, householdLine } from './familyHint';
import { buildQuickQuestions, type QuickQuestionId } from './familyQuestions';

export function FamilyQuickQuestions({ familyId }: { readonly familyId: string }) {
  const oportunidades = useOportunidades(familyId, 'prioridad');
  // Misma caché que la ficha: solo para la línea que recuerda el hogar (pantalla, nunca se envía).
  const detail = useFamilia(familyId).data?.body.data;
  const names = useLocalNames();
  const [open, setOpen] = useState<QuickQuestionId | null>(null);
  const titleId = useId();
  if (oportunidades.isPending) return <Skeleton rows={1} />;
  if (oportunidades.data === undefined) return null;
  const reminder = detail === undefined ? null : householdLine(detail.composition, detail.rsh_band, firstName(familyId, names));
  const questions = buildQuickQuestions(oportunidades.data.body.items, names.get(familyId) ?? null, reminder);
  const selected = questions.find((q) => q.id === open);
  return (
    <Card className="space-y-3" aria-labelledby={titleId}>
      <h2 id={titleId}>{DEMO_COPY.quickTitle}</h2>
      {questions.length === 0 ? (
        <p>{DEMO_COPY.quickNoData}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {questions.map((q) => (
            <Button
              key={q.id}
              variant={q.id === open ? 'primary' : 'secondary'}
              className="w-full justify-start text-left"
              aria-expanded={q.id === open}
              onClick={() => setOpen(q.id === open ? null : q.id)}
            >
              {q.question}
            </Button>
          ))}
        </div>
      )}
      {selected !== undefined && (
        <div aria-live="polite" className="space-y-2 rounded-xl bg-canvas p-3">
          <ul className="list-disc space-y-1 pl-5">
            {selected.lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <ReferentialNotice />
        </div>
      )}
      <FamilyChat familyId={familyId} />
    </Card>
  );
}

export default FamilyQuickQuestions;
