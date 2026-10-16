// "Agregar información" de una familia EXISTENTE (cambio 5, DEC-039; orientada al caso, DEC-093).
// Preguntas CERRADAS solo para los datos que le faltan a sus beneficios de "Falta información"
// (missing_codes de C3), ordenadas de forma determinista por impacto (cuántos INDETERMINADO destraba
// cada respuesta; empate: `position` del motor) y SIN LLM (questionPlan.ts). Se muestran
// MAX_PRIMARY_QUESTIONS y el resto tras "Ver más preguntas"; cada una dice qué apoyos puede abrir (por
// nombre legible, nunca el código) y lleva una pista corta del caso. Lo ya declarado (GET
// /antecedentes `declared_fields`) no se vuelve a preguntar. Con "No sé" (→ null; vivienda → UNKNOWN);
// sin texto libre, nombres ni contacto. Semanas solo tras "Sí" a embarazo, con el umbral del motor o
// texto sin número. Un código sin campo cerrado se muestra solo como guía. Envía la operación PROPUESTA
// POST /familias/{id}/antecedentes (fuera de C3): solo en línea, sin cola, y oculta en `escala` o sin
// `capabilities.addInfo`. La re-evaluación (PRELIMINAR) la hace la API; al guardar se muestra qué
// apoyos cambiaron según ese recálculo y se vuelve a la ficha.
import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { declaredFieldsOf, getFamiliaAntecedentes } from '../../api/proposals/addInfo';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { AddFamilyInfoRequestV1, AddInfoField } from '../../api/proposals/types';
import type { FamilyContextView, FamilyDetail, Opportunity } from '../../api/types';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../../config/profile';
import { useSubmitAddInfo } from '../../data/mutations';
import { useContexto, useFamilia, useOportunidades } from '../../data/queries';
import { benefitSections } from '../../domain/benefitGroups';
import { familyDisplayName } from '../../domain/familyName';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
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
  answerLabel,
  answerValue,
  EMPTY_ANSWERS,
  isFutureDate,
  keepsIdempotencyKey,
  QuestionField,
  questionLabel,
  type AddInfoQuestionKey,
  type Answers,
} from '../new-family/questions';
import NotFoundPage from '../system/NotFoundPage';
import { diffAfterSave, parentOf, planQuestions, plannedFields, type AfterSaveDiff, type ChangedBenefit, type PlannedQuestion } from './questionPlan';

/** rsh_band y los dependientes solo se preguntan si también se pregunta su padre y la respuesta es "Sí". */
function isVisible(key: AddInfoQuestionKey, answers: Answers, fields: readonly AddInfoQuestionKey[]): boolean {
  if (key === 'rsh_band' && fields.includes('has_rsh') && answers.has_rsh !== 'yes') return false;
  const parent = parentOf(key);
  return parent === null || !fields.includes(parent) || answers[parent] === 'yes';
}

/** Preguntas sensibles: se avisan como opcionales ("Si desea responder"). */
const SENSITIVE: ReadonlySet<AddInfoQuestionKey> = new Set<AddInfoQuestionKey>(['household_pregnancy', 'pregnancy_weeks_at_least_threshold', 'child_possible_disability']);

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

/** GET previo (fuera de C3): umbral N y campos ya declarados. Siempre se pide; si falla, sin filtro ni N. */
function useAntecedentes(familyId: string) {
  return useQuery({
    queryKey: ['antecedentes', familyId],
    retry: false,
    staleTime: Infinity,
    queryFn: ({ signal }) => getFamiliaAntecedentes({ familyId, signal }),
  });
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

function ResultList({ title, items }: { readonly title: string; readonly items: readonly ChangedBenefit[] }) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-1">
      <h3 className="font-semibold">{title}</h3>
      <ul className="list-disc space-y-1 pl-6">
        {items.map((item, index) => (
          <li key={`${index}-${item.name}`}>
            {item.name}
            {item.reason !== null && <span className="text-sm text-ink-muted"> ({item.reason})</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AddInfoResult({ familyId, result }: { readonly familyId: string; readonly result: AfterSaveDiff }) {
  const navigate = useNavigate();
  const unchanged = result.nowApplies.length === 0 && result.notListed.length === 0;
  return (
    <Card role="status" className="space-y-4">
      <h2>{ADD_INFO_COPY.resultTitle}</h2>
      <ResultList title={ADD_INFO_COPY.nowApplies} items={result.nowApplies} />
      <ResultList title={ADD_INFO_COPY.stillMissing} items={result.stillMissing} />
      <ResultList title={ADD_INFO_COPY.notListed} items={result.notListed} />
      {unchanged && <p className="text-ink-muted">{ADD_INFO_COPY.noChange}</p>}
      <Button icon="chevron-left" data-primary-action onClick={() => void navigate(familyRoutes.ficha(familyId), { state: { addInfoDone: true } })}>
        {ADD_INFO_COPY.backToFamily}
      </Button>
    </Card>
  );
}

function AddInfoForm({ familyId, detail, opportunities, context }: {
  readonly familyId: string;
  readonly detail: FamilyDetail;
  readonly opportunities: readonly Opportunity[];
  readonly context: FamilyContextView | null;
}) {
  const online = useOnline();
  const mutation = useSubmitAddInfo();
  const antecedentes = useAntecedentes(familyId);
  const moreId = useId();
  const [answers, setAnswers] = useState<Answers>(EMPTY_ANSWERS);
  const [attempt, setAttempt] = useState<{ canonical: string; key: string } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [showMore, setShowMore] = useState(false);
  const [result, setResult] = useState<AfterSaveDiff | null>(null);

  if (result !== null) return <AddInfoResult familyId={familyId} result={result} />;
  // La lista depende de lo ya declarado: se muestra cuando el GET termina (éxito o error).
  if (antecedentes.isPending) return <Skeleton rows={3} rowClass="h-16" />;

  const weeks = antecedentes.data?.body.data.pregnancy_weeks_threshold ?? null;
  const declared = declaredFieldsOf(antecedentes.data?.body);
  const plan = planQuestions({ detail, opportunities, declared, context });
  // Las respuestas de preguntas ocultas tras "Ver más" se conservan y se envían.
  const fields = plannedFields(plan);
  const body = buildAddInfoBody(answers, fields);
  const answered = Object.keys(body).length - 1;
  const futureDate = isFutureDate(answers.last_child_health_control_date);
  const blocked = answered === 0 || futureDate || !online;

  if (plan.pendingBenefits === 0) {
    return (
      <div className="space-y-5">
        <p>{ADD_INFO_COPY.noPending}</p>
        <ReferentialNotice />
      </div>
    );
  }

  const update = (key: AddInfoQuestionKey, value: string) => {
    setAnswers((current) => ({ ...current, [key]: value }));
    setError(null);
  };

  const submit = () => {
    if (blocked) return;
    const canonical = JSON.stringify(body);
    // Mismo cuerpo ⇒ misma clave; cualquier edición cambia el cuerpo ⇒ clave nueva.
    const current = attempt !== null && attempt.canonical === canonical ? attempt : { canonical, key: uuid() };
    // La mutación reemplaza la ficha en caché: se guarda el "antes" para comparar.
    const beforeRows = benefitSections(detail, opportunities).missing;
    const answeredText = new Map<AddInfoField, string>(
      fields.filter((key) => key in body).map((key) => [key, answerLabel(ADD_INFO_QUESTIONS[key], answers[key])]),
    );
    setAttempt(current);
    setError(null);
    mutation
      .mutateAsync({ familyId, body, idempotencyKey: current.key })
      .then((ok) => {
        setAttempt(null);
        setResult(diffAfterSave(beforeRows, ok.body.data, opportunities, answeredText, weeks));
      })
      .catch((failure: unknown) => {
        if (!keepsIdempotencyKey(failure)) setAttempt(null);
        setError(failure);
      });
  };

  const renderQuestion = (question: PlannedQuestion) => (
    <div key={question.key} className="space-y-2">
      <QuestionField question={ADD_INFO_QUESTIONS[question.key]} value={answers[question.key]} onChange={(value) => update(question.key, value)} label={labelFor(question.key, weeks)} />
      {question.opens.length > 0 && <p className="text-sm text-ink-muted">{ADD_INFO_COPY.opens(question.opens.join(', '))}</p>}
      {question.completes.length > 0 && <p className="text-sm text-ink-muted">{ADD_INFO_COPY.completes(question.completes.join(', '))}</p>}
      {question.hint !== null && <p className="text-sm text-ink-muted">{question.hint}</p>}
      {question.dependents
        .filter((key) => isVisible(key, answers, fields))
        .map((key) => (
          <QuestionField key={key} question={ADD_INFO_QUESTIONS[key]} value={answers[key]} onChange={(value) => update(key, value)} label={labelFor(key, weeks)} />
        ))}
    </div>
  );

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
          {plan.primary.map(renderQuestion)}
          {plan.more.length > 0 && (
            <>
              <div id={moreId} className="space-y-5" hidden={!showMore}>
                {showMore && plan.more.map(renderQuestion)}
              </div>
              <Button variant="ghost" aria-expanded={showMore} aria-controls={moreId} onClick={() => setShowMore((open) => !open)}>
                {showMore ? ADD_INFO_COPY.fewerQuestions : ADD_INFO_COPY.moreQuestions(formatInteger(plan.more.length))}
              </Button>
            </>
          )}
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

      {plan.guide.length > 0 && (
        <Card className="space-y-2">
          <h2>{t('add_info.guide_title')}</h2>
          <p className="text-ink-muted">{t('add_info.guide_hint')}</p>
          <ul className="list-disc space-y-1 pl-6">
            {plan.guide.map((line) => (
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
  // Solo para la pista de contexto (señales de urgencia); si falla o tarda, la pista va sin señales.
  const contexto = useContexto(familyId, ficha.isSuccess);

  let body;
  if (ficha.isPending) body = <Skeleton rows={3} rowClass="h-16" />;
  else if (ficha.isError && ficha.data === undefined) body = <ErrorState error={ficha.error} onRetry={() => void ficha.refetch()} />;
  else
    body = (
      <AddInfoForm
        familyId={familyId}
        detail={ficha.data.body.data}
        opportunities={prioridad.data?.body.items ?? []}
        context={contexto.data?.body.data ?? null}
      />
    );

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
