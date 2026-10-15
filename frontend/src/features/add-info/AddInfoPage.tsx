// "Agregar información" de una familia EXISTENTE (cambio 5, DEC-039). Preguntas CERRADAS solo para
// los datos que le faltan a sus beneficios (missing_codes de C3), con "No sé" (→ null; vivienda →
// UNKNOWN). Sin texto libre, nombres ni contacto. Reutiliza los controles de Familia nueva. Un código
// sin campo cerrado equivalente muestra la pregunta sugerida de C3 solo como guía (DEC-039). Envía
// la operación PROPUESTA POST /familias/{id}/antecedentes (fuera de C3): solo en línea, sin cola, y
// oculta en `escala` o sin `capabilities.addInfo`. La re-evaluación (PRELIMINAR) la hace la API.
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { fieldForMissingCode } from '../../api/proposals/addInfo';
import type { AddFamilyInfoRequestV1 } from '../../api/proposals/types';
import type { FamilyDetail, MissingCode, Opportunity } from '../../api/types';
import { runtimeConfig, SYNTHETIC_CLASSIFICATION } from '../../config/profile';
import { useSubmitAddInfo } from '../../data/mutations';
import { useFamilia, useOportunidades } from '../../data/queries';
import { familyMissingCodes, groupBenefits } from '../../domain/benefitGroups';
import { familyDisplayName } from '../../domain/familyName';
import { isValidId } from '../../domain/ids';
import { MISSING_CODE_KEY } from '../../domain/presentation';
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
  answerValue,
  EMPTY_ANSWERS,
  isFutureDate,
  keepsIdempotencyKey,
  QUESTION_ORDER,
  QUESTIONS,
  QuestionField,
  type Answers,
  type QuestionKey,
} from '../new-family/questions';
import NotFoundPage from '../system/NotFoundPage';

const isMissingCode = (code: string): code is MissingCode => Object.prototype.hasOwnProperty.call(MISSING_CODE_KEY, code);

/** rsh_band solo se pregunta si también se pregunta has_rsh y la respuesta es "Sí". */
function isVisible(key: QuestionKey, answers: Answers, fields: readonly QuestionKey[]): boolean {
  return key !== 'rsh_band' || !fields.includes('has_rsh') || answers.has_rsh === 'yes';
}

/** Cuerpo con SOLO las preguntas respondidas (sin responder = sin cambio); "No sé" → null / UNKNOWN. */
export function buildAddInfoBody(answers: Answers, fields: readonly QuestionKey[]): AddFamilyInfoRequestV1 {
  const body: Record<string, unknown> = { data_classification: SYNTHETIC_CLASSIFICATION };
  for (const key of fields) {
    if (!isVisible(key, answers, fields) || answers[key] === '') continue;
    body[key] = answerValue(key, answers[key]);
  }
  return body as AddFamilyInfoRequestV1;
}

interface GuideItem {
  readonly code: string;
  readonly lines: readonly string[];
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
  const mapped = new Set(codes.map(fieldForMissingCode).filter((field): field is QuestionKey => field !== null));
  const fields = QUESTION_ORDER.filter((key) => mapped.has(key));
  const { applies, missing } = groupBenefits(detail, opportunities);
  const rows = [...missing, ...applies];
  const guide: GuideItem[] = codes
    .filter((code) => fieldForMissingCode(code) === null)
    .map((code) => {
      const questions = [...new Set(rows.filter((row) => row.missingCodes.includes(code)).flatMap((row) => row.questions))];
      const label = isMissingCode(code) ? t(MISSING_CODE_KEY[code]) : t('family.missing_generic');
      return { code, lines: questions.length > 0 ? questions : [label] };
    });

  const body = buildAddInfoBody(answers, fields);
  const answered = Object.keys(body).length - 1;
  const futureDate = isFutureDate(answers.last_child_health_control_date);
  const blocked = answered === 0 || futureDate || !online;

  const update = (key: QuestionKey, value: string) => {
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
              <QuestionField key={key} question={QUESTIONS[key]} value={answers[key]} onChange={(value) => update(key, value)} />
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
            {guide.flatMap((item) =>
              item.lines.map((line) => (
                <li key={`${item.code}-${line}`} className="c3-text">
                  {line}
                </li>
              )),
            )}
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
