// Familia nueva / preevaluación (design.md §9.6, FE-001/FE-003): 4 pasos de preguntas CERRADAS en
// memoria + revisión. Toda pregunta admite "No sé" (→ null; vivienda → UNKNOWN, SUP-034). Sin
// nombres, identificadores, contacto ni texto libre. Solo existe en local/demo (SUP-038). El
// resultado PRELIMINAR lo decide C3; el cliente solo arma el cuerpo explícito y lo muestra.
// Las preguntas y sus controles viven en ./questions.tsx (compartidas con "Agregar información").
import { useEffect, useId, useRef, useState } from 'react';
import type { JardinSummary, PreevaluationRequest, PreevaluationResult } from '../../api/types';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../../config/profile';
import { useSubmitPreevaluation } from '../../data/mutations';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { uuid } from '../../lib/uuid';
import { Button, ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { PageTitle } from '../../ui/PageTitle';
import { Banner, EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { OpportunityCard } from '../family/OpportunityCard';
import { familyRoutes } from '../family/routes';
import NotFoundPage from '../system/NotFoundPage';
import { useSelectedGarden } from '../system/useSelectedGarden';
import {
  answerLabel,
  EMPTY_ANSWERS,
  HOUSING,
  INCOME_BANDS,
  isFutureDate,
  keepsIdempotencyKey,
  LABEL,
  QUESTIONS,
  QuestionField,
  RSH_BANDS,
  UNKNOWN,
  type Answers,
  type Question,
  type QuestionKey,
} from './questions';

const q = (key: QuestionKey): Question => QUESTIONS[key];

const STEPS: readonly { readonly titleKey: PlainCopyKey; readonly questions: readonly Question[] }[] = [
  {
    titleKey: 'new_family.step.child',
    questions: [q('child_age'), q('siblings_under_6'), q('siblings_6_14'), q('siblings_15_18')],
  },
  {
    titleKey: 'new_family.step.rsh_income',
    questions: [q('has_rsh'), q('rsh_band'), q('household_income_band')],
  },
  {
    titleKey: 'new_family.step.programs_health',
    questions: [
      q('ssyo_participation'),
      q('chile_crece_contigo_access'),
      q('last_child_health_control_date'),
      q('child_possible_disability'),
      q('child_in_therapy'),
      q('housing_type'),
    ],
  },
  {
    titleKey: 'new_family.step.extra',
    questions: [
      q('household_pregnancy'),
      q('household_has_adult_over_65'),
      q('household_formal_employment_or_pension'),
      q('household_water_payment_difficulty'),
      q('household_food_purchase_difficulty'),
    ],
  },
];
const REVIEW_STEP = STEPS.length;
const TOTAL_STEPS = STEPS.length + 1;
const DATE_STEP = 2;

/** rsh_band solo se pregunta si el hogar dice tener RSH. */
const isVisible = (question: Question, answers: Answers): boolean => question.key !== 'rsh_band' || answers.has_rsh === 'yes';

/** Cuerpo EXPLÍCITO con todas las claves (§9.6); "No sé" y sin responder → null (SUP-034). */
export function buildPreevaluationBody(answers: Answers, garden: JardinSummary): PreevaluationRequest {
  const int = (value: string): number | null => (value === '' || value === UNKNOWN ? null : Number(value));
  const yesNo = (value: string): boolean | null => (value === 'yes' ? true : value === 'no' ? false : null);
  const hasRsh = yesNo(answers.has_rsh);
  return {
    data_classification: SYNTHETIC_CLASSIFICATION,
    garden_id: garden.garden_id,
    commune_id: garden.commune_id,
    demo_notice_accepted: true,
    child_age: int(answers.child_age),
    siblings_under_6: int(answers.siblings_under_6),
    siblings_6_14: int(answers.siblings_6_14),
    siblings_15_18: int(answers.siblings_15_18),
    has_rsh: hasRsh,
    rsh_band: hasRsh === true ? (RSH_BANDS.find((band) => String(band) === answers.rsh_band) ?? null) : null,
    household_income_band: INCOME_BANDS.find((band) => band === answers.household_income_band) ?? null,
    ssyo_participation: yesNo(answers.ssyo_participation),
    chile_crece_contigo_access: yesNo(answers.chile_crece_contigo_access),
    last_child_health_control_date: answers.last_child_health_control_date === '' ? null : answers.last_child_health_control_date,
    child_possible_disability: yesNo(answers.child_possible_disability),
    child_in_therapy: yesNo(answers.child_in_therapy),
    housing_type: answers.housing_type === UNKNOWN ? 'UNKNOWN' : (HOUSING.find((h) => h === answers.housing_type) ?? null),
    household_pregnancy: yesNo(answers.household_pregnancy),
    household_has_adult_over_65: yesNo(answers.household_has_adult_over_65),
    household_formal_employment_or_pension: yesNo(answers.household_formal_employment_or_pension),
    household_water_payment_difficulty: yesNo(answers.household_water_payment_difficulty),
    household_food_purchase_difficulty: yesNo(answers.household_food_purchase_difficulty),
  };
}

function PreevaluationResultView({ result, onRestart }: { readonly result: PreevaluationResult; readonly onRestart: () => void }) {
  return (
    <div className="space-y-5">
      <Card className="space-y-2">
        <h2>{t('new_family.result_title')}</h2>
        <Chip icon="info" tone="other" label={t('level.preliminar')} />
        <p>{t('new_family.result_level')}</p>
      </Card>
      {result.opportunities.length === 0 ? (
        <EmptyState message={t('empty.opportunities')} />
      ) : (
        <div className="space-y-4">
          {result.opportunities.map((opportunity) => (
            <OpportunityCard key={opportunity.benefit_id} opportunity={opportunity} result={undefined} />
          ))}
        </div>
      )}
      {result.questions.length > 0 && (
        <section aria-labelledby="new-family-questions" className="space-y-2">
          <h2 id="new-family-questions">{t('new_family.questions_title')}</h2>
          <ul className="list-disc space-y-1 pl-6">
            {result.questions.map((question) => (
              <li key={question} className="c3-text">
                {question}
              </li>
            ))}
          </ul>
        </section>
      )}
      <ReferentialNotice />
      <div className="flex flex-col gap-2">
        {isValidId(result.family_id) && (
          <ButtonLink to={familyRoutes.ficha(result.family_id)} icon="user" data-primary-action className="w-full">
            {t('new_family.go_to_family')}
          </ButtonLink>
        )}
        <Button variant="secondary" icon="refresh" className="w-full" onClick={onRestart}>
          {t('new_family.start_over')}
        </Button>
      </div>
    </div>
  );
}

function NewFamilyForm({ garden, gardens, onSelectGarden }: {
  readonly garden: JardinSummary;
  readonly gardens: readonly JardinSummary[];
  readonly onSelectGarden: (gardenId: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [accepted, setAccepted] = useState(false);
  const [answers, setAnswers] = useState<Answers>(EMPTY_ANSWERS);
  const [attempt, setAttempt] = useState<{ canonical: string; key: string } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<PreevaluationResult | null>(null);
  const mutation = useSubmitPreevaluation();
  const stepHeading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);
  const acceptId = useId();

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    stepHeading.current?.focus();
  }, [step, result]);

  const restart = () => {
    setStep(0);
    setAccepted(false);
    setAnswers(EMPTY_ANSWERS);
    setAttempt(null);
    setError(null);
    setResult(null);
  };

  if (result !== null) return <PreevaluationResultView result={result} onRestart={restart} />;

  const update = (key: QuestionKey, value: string) => {
    setAnswers((current) => ({ ...current, [key]: value }));
    setError(null);
  };

  const submit = () => {
    const body = buildPreevaluationBody(answers, garden);
    const canonical = JSON.stringify(body);
    // Mismo cuerpo ⇒ misma clave; cualquier edición (o cambio de jardín) cambia el cuerpo ⇒ clave nueva.
    const current = attempt !== null && attempt.canonical === canonical ? attempt : { canonical, key: uuid() };
    setAttempt(current);
    setError(null);
    mutation
      .mutateAsync({ body, idempotencyKey: current.key })
      .then((ok) => {
        setAttempt(null);
        setResult(ok.body.data);
      })
      .catch((failure: unknown) => {
        if (!keepsIdempotencyKey(failure)) setAttempt(null);
        setError(failure);
      });
  };

  const blocked = (step === 0 && !accepted) || (step === DATE_STEP && isFutureDate(answers.last_child_health_control_date));
  const current = STEPS[step];

  return (
    <div className="space-y-5">
      <p className="text-ink-muted">{t('new_family.step', { current: formatInteger(step + 1), total: formatInteger(TOTAL_STEPS) })}</p>
      <h2 ref={stepHeading} tabIndex={-1} className="focus:outline-none">
        {t(current?.titleKey ?? 'new_family.step.review')}
      </h2>

      {step === 0 && (
        <Card className="space-y-3">
          <p className="font-semibold">{t('new_family.demo_notice')}</p>
          <label htmlFor={acceptId} className="flex min-h-12 cursor-pointer items-center gap-3 font-semibold">
            <input
              id={acceptId}
              type="checkbox"
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
              className="size-6 shrink-0 accent-primary"
            />
            <span>
              {t('new_family.demo_notice_accept')} {t('a11y.required')}
            </span>
          </label>
          <p className="text-ink-muted">{t('new_family.no_text_note')}</p>
        </Card>
      )}
      {step === 0 && gardens.length > 1 && (
        <ChoiceChips
          legend={t('home.select_garden')}
          options={gardens.map((g) => ({ value: g.garden_id, label: t('home.garden_label', { garden_id: g.garden_id }) }))}
          value={garden.garden_id}
          onChange={onSelectGarden}
        />
      )}

      {current !== undefined ? (
        <div className="space-y-5">
          {current.questions
            .filter((question) => isVisible(question, answers))
            .map((question) => (
              <QuestionField key={question.key} question={question} value={answers[question.key]} onChange={(value) => update(question.key, value)} />
            ))}
        </div>
      ) : (
        <Card>
          <dl className="space-y-3">
            <div>
              <dt className="text-ink-muted">{t('home.select_garden')}</dt>
              <dd className="font-semibold">{t('home.garden_label', { garden_id: garden.garden_id })}</dd>
            </div>
            {STEPS.flatMap((s) => s.questions)
              .filter((question) => isVisible(question, answers))
              .map((question) => (
                <div key={question.key}>
                  <dt className="text-ink-muted">{t(LABEL[question.key])}</dt>
                  <dd className="font-semibold">{answerLabel(question, answers[question.key])}</dd>
                </div>
              ))}
          </dl>
        </Card>
      )}

      {error !== null && <ErrorState error={error} onRetry={submit} />}

      <div className="flex gap-2">
        {step > 0 && (
          <Button variant="secondary" icon="chevron-left" className="flex-1" onClick={() => setStep(step - 1)}>
            {t('common.previous')}
          </Button>
        )}
        {step < REVIEW_STEP ? (
          <Button data-primary-action className="flex-1" disabled={blocked} onClick={() => setStep(step + 1)}>
            {t('common.continue')}
          </Button>
        ) : (
          <Button icon="check" data-primary-action className="flex-1" busy={mutation.isPending} onClick={submit}>
            {mutation.isPending ? t('new_family.submitting') : t('new_family.submit')}
          </Button>
        )}
      </div>
    </div>
  );
}

function NewFamilyView() {
  const { jardines, gardens, garden, select } = useSelectedGarden();
  let body;
  if (jardines.isPending) body = <Skeleton rows={3} />;
  else if (jardines.isError && jardines.data === undefined) body = <ErrorState error={jardines.error} onRetry={() => void jardines.refetch()} />;
  else if (garden === undefined) body = <EmptyState message={t('empty.gardens')} />;
  else body = <NewFamilyForm garden={garden} gardens={gardens} onSelectGarden={select} />;
  return (
    <div className="space-y-4">
      <PageTitle>{t('new_family.title')}</PageTitle>
      <Banner tone="info">{t('new_family.intro')}</Banner>
      {body}
    </div>
  );
}

export default function NewFamilyPage() {
  // SUP-038: en `escala` la ruta no existe (sin pestaña ni request).
  if (!runtimeConfig().capabilities.newFamily) return <NotFoundPage />;
  return <NewFamilyView />;
}
