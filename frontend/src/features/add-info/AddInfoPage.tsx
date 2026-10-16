// "Agregar información" de una familia EXISTENTE (cambio 5, DEC-039). Preguntas CERRADAS solo para
// los datos que le faltan a sus beneficios (missing_codes de C3), con "No sé" (→ null; vivienda →
// UNKNOWN). Sin texto libre, nombres ni contacto. Reutiliza los controles de Familia nueva. Los
// códigos del motor usan booleanos de la propuesta (semanas solo tras "Sí" a embarazo; umbral del
// motor o texto sin número); las preguntas sensibles se marcan opcionales. Un código sin campo
// cerrado muestra la pregunta sugerida de C3 o su etiqueta solo como guía, sin repetir (DEC-039). Envía
// la operación PROPUESTA POST /familias/{id}/antecedentes (fuera de C3): solo en línea, sin cola, y
// oculta en `escala` o sin `capabilities.addInfo`. La re-evaluación (PRELIMINAR) la hace la API.
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { DEPENDENT_FIELDS, fieldForMissingCode, getFamiliaAntecedentes } from '../../api/proposals/addInfo';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { AddFamilyInfoRequestV1 } from '../../api/proposals/types';
import type { FamilyDetail, Opportunity } from '../../api/types';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../../config/profile';
import { useSubmitAddInfo } from '../../data/mutations';
import { useFamilia, useOportunidades } from '../../data/queries';
import { familyMissingCodes, groupBenefits, uniqueTexts } from '../../domain/benefitGroups';
import { familyDisplayName } from '../../domain/familyName';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
import { missingCodeLabels } from '../../domain/presentation';
import { t } from '../../i18n/copy';
import { uuid } from '../../lib/uuid';
import { useLocalNames } from '../../offline/localNames';
import { useOnline } from '../../offline/network';
import { Button, ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { PageTitle } from '../../ui/PageTitle';
import { Banner, EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { familyRoutes } from '../family/routes';
import {
  ADD_INFO_QUESTIONS,
  answerValue,
  EMPTY_ANSWERS,
  isFutureDate,
  keepsIdempotencyKey,
  QUESTION_ORDER,
  QuestionField,
  questionLabel,
  type AddInfoQuestionKey,
  type Answers,
} from '../new-family/questions';
import NotFoundPage from '../system/NotFoundPage';

/** Campo padre de un campo dependiente (p. ej. semanas → embarazo), si lo hay. */
function parentOf(key: AddInfoQuestionKey): AddInfoQuestionKey | null {
  for (const [parent, children] of Object.entries(DEPENDENT_FIELDS)) {
    if (children?.includes(key)) return parent as AddInfoQuestionKey;
  }
  return null;
}

/** rsh_band y los dependientes solo se preguntan si también se pregunta su padre y la respuesta es "Sí". */
function isVisible(key: AddInfoQuestionKey, answers: Answers, fields: readonly AddInfoQuestionKey[]): boolean {
  if (key === 'rsh_band' && fields.includes('has_rsh') && answers.has_rsh !== 'yes') return false;
  const parent = parentOf(key);
  return parent === null || !fields.includes(parent) || answers[parent] === 'yes';
}

/** Preguntas sensibles: se avisan como opcionales ("Si desea responder"). */
const SENSITIVE: ReadonlySet<AddInfoQuestionKey> = new Set<AddInfoQuestionKey>(['household_pregnancy', 'pregnancy_weeks_at_least_threshold', 'child_possible_disability']);

/** Campos a preguntar: los de cada código faltante más sus dependientes, en el orden de la ficha. */
function fieldsFor(codes: readonly string[]): AddInfoQuestionKey[] {
  const mapped = new Set(codes.map(fieldForMissingCode).filter((field): field is AddInfoQuestionKey => field !== null));
  for (const field of [...mapped]) for (const child of DEPENDENT_FIELDS[field] ?? []) mapped.add(child);
  return QUESTION_ORDER.filter((key) => mapped.has(key));
}

/**
 * Texto de la pregunta: semanas con el umbral N del motor si se conoce (si no, texto sin número, nunca
 * uno fijo); las sensibles llevan "si desea responder" en la misma leyenda/etiqueta.
 */
function labelFor(key: AddInfoQuestionKey, weeks: number | null): string | undefined {
  let label: string | undefined;
  if (key === 'pregnancy_weeks_at_least_threshold') {
    label = weeks === null ? ADD_INFO_COPY.pregnancyWeeksMin : ADD_INFO_COPY.pregnancyWeeksN(formatInteger(weeks));
  }
  return SENSITIVE.has(key) ? ADD_INFO_COPY.optionalSensitive(label ?? questionLabel(key)) : label;
}

/** Umbral N (GET previo, fuera de C3): solo si se va a preguntar por semanas; si falla, null. */
function useWeeksThreshold(familyId: string, enabled: boolean): number | null {
  const query = useQuery({
    queryKey: ['antecedentes', familyId],
    enabled,
    retry: false,
    staleTime: Infinity,
    queryFn: ({ signal }) => getFamiliaAntecedentes({ familyId, signal }),
  });
  return query.data?.body.data.pregnancy_weeks_threshold ?? null;
}

/** Cuerpo con SOLO las preguntas respondidas (sin responder = sin cambio); "No sé" → null / UNKNOWN. */
export function buildAddInfoBody(answers: Answers, fields: readonly AddInfoQuestionKey[]): AddFamilyInfoRequestV1 {
  const body: Record<string, unknown> = { data_classification: SYNTHETIC_CLASSIFICATION };
  for (const key of fields) {
    if (!isVisible(key, answers, fields) || answers[key] === '') continue;
    body[key] = answerValue(key, answers[key]);
  }
  return body as AddFamilyInfoRequestV1;
}

function AddInfoForm({ familyId, detail, opportunities }: {
  readonly familyId: string;
  readonly detail: FamilyDetail;
  readonly opportunities: readonly Opportunity[];
}) {
  const navigate = useNavigate();
  const online = useOnline();
  const mutation = useSubmitAddInfo();
  const [answers, setAnswers] = useState<Answers>(EMPTY_ANSWERS);
  const [attempt, setAttempt] = useState<{ canonical: string; key: string } | null>(null);
  const [error, setError] = useState<unknown>(null);

  const codes = familyMissingCodes(detail);
  const fields = fieldsFor(codes);
  const weeks = useWeeksThreshold(familyId, fields.includes('pregnancy_weeks_at_least_threshold'));
  const { applies, missing } = groupBenefits(detail, opportunities);
  const rows = [...missing, ...applies];
  // Guía (sin campo cerrado), sin repetir textos: las preguntas de C3 de beneficios a los que solo les
  // faltan datos sin campo, y la etiqueta simple de los demás datos sin campo.
  const noField = (code: string) => fieldForMissingCode(code) === null;
  const guideRows = rows.filter((row) => row.missingCodes.length > 0 && row.missingCodes.every(noField) && row.questions.length > 0);
  const covered = new Set(guideRows.flatMap((row) => row.missingCodes));
  const guide = uniqueTexts([
    ...guideRows.flatMap((row) => row.questions),
    ...missingCodeLabels(codes.filter((code) => noField(code) && !covered.has(code))),
  ]);
  const body = buildAddInfoBody(answers, fields);
  const answered = Object.keys(body).length - 1;
  const futureDate = isFutureDate(answers.last_child_health_control_date);
  const blocked = answered === 0 || futureDate || !online;

  const update = (key: AddInfoQuestionKey, value: string) => {
    setAnswers((current) => ({ ...current, [key]: value }));
    setError(null);
  };

  const submit = () => {
    if (blocked) return;
    const canonical = JSON.stringify(body);
    // Mismo cuerpo ⇒ misma clave; cualquier edición cambia el cuerpo ⇒ clave nueva.
    const current = attempt !== null && attempt.canonical === canonical ? attempt : { canonical, key: uuid() };
    setAttempt(current);
    setError(null);
    mutation
      .mutateAsync({ familyId, body, idempotencyKey: current.key })
      .then(() => {
        setAttempt(null);
        void navigate(familyRoutes.ficha(familyId), { state: { addInfoDone: true } });
      })
      .catch((failure: unknown) => {
        if (!keepsIdempotencyKey(failure)) setAttempt(null);
        setError(failure);
      });
  };

  return (
    <div className="space-y-5">
      {fields.length === 0 ? (
        <EmptyState message={t('add_info.no_fields')} />
      ) : (
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          {fields
            .filter((key) => isVisible(key, answers, fields))
            .map((key) => (
              <QuestionField key={key} question={ADD_INFO_QUESTIONS[key]} value={answers[key]} onChange={(value) => update(key, value)} label={labelFor(key, weeks)} />
            ))}
          {!online && (
            <Banner tone="warn" icon="wifi-off">
              {t('add_info.offline')}
            </Banner>
          )}
          {answered === 0 && <p className="text-ink-muted">{t('add_info.answer_one')}</p>}
          {error !== null && <ErrorState error={error} onRetry={submit} />}
          <Button type="submit" icon="check" data-primary-action className="w-full" disabled={blocked} busy={mutation.isPending}>
            {mutation.isPending ? t('add_info.submitting') : t('add_info.submit')}
          </Button>
        </form>
      )}

      {guide.length > 0 && (
        <Card className="space-y-2">
          <h2>{t('add_info.guide_title')}</h2>
          <p className="text-ink-muted">{t('add_info.guide_hint')}</p>
          <ul className="list-disc space-y-1 pl-6">
            {guide.map((line) => (
              <li key={line} className="c3-text">
                {line}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <ReferentialNotice />
    </div>
  );
}

function AddInfoView({ familyId }: { readonly familyId: string }) {
  const names = useLocalNames();
  const ficha = useFamilia(familyId);
  const prioridad = useOportunidades(familyId, 'prioridad', ficha.isSuccess);

  let body;
  if (ficha.isPending) body = <Skeleton rows={3} rowClass="h-16" />;
  else if (ficha.isError && ficha.data === undefined) body = <ErrorState error={ficha.error} onRetry={() => void ficha.refetch()} />;
  else body = <AddInfoForm familyId={familyId} detail={ficha.data.body.data} opportunities={prioridad.data?.body.items ?? []} />;

  return (
    <div className="space-y-4">
      <ButtonLink to={familyRoutes.ficha(familyId)} variant="ghost" icon="chevron-left" className="-ml-3">
        {t('nav.back')}
      </ButtonLink>
      <PageTitle>{t('add_info.title')}</PageTitle>
      <p className="font-semibold">{familyDisplayName(familyId, names)}</p>
      <p>{t('add_info.intro')}</p>
      <p className="text-ink-muted">{t('new_family.no_text_note')}</p>
      {body}
    </div>
  );
}

export default function AddInfoPage() {
  const { familyId } = useParams();
  // DEC-039: sin la capacidad (escala, o API real sin VITE_PROPOSAL_ADD_INFO=true) la ruta no existe.
  if (!runtimeConfig().capabilities.addInfo || !isValidId(familyId)) return <NotFoundPage />;
  return <AddInfoView key={familyId} familyId={familyId} />;
}
