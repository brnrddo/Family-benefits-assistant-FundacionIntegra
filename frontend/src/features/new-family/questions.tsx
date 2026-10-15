// Preguntas CERRADAS de la ficha (design.md §9.6), compartidas por Familia nueva y por "Agregar
// información" (DEC-039). Cada pregunta corresponde a un campo cerrado de PreevaluationRequest de C3
// (o, solo en "Agregar información", a un booleano de la propuesta fuera de C3) y admite "No sé" (→ null; vivienda → UNKNOWN, SUP-034). Sin nombres, identificadores, contacto ni
// texto libre.
import { useId } from 'react';
import { isApiError, isInvalidResponse } from '../../api/errors';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { AddFamilyInfoRequestV1, AddInfoExtraField, AddInfoField, C3AddInfoField } from '../../api/proposals/types';
import type { HousingType, IncomeBand } from '../../api/types';
import { formatDate, formatInteger } from '../../domain/format';
import { HOUSING_KEY, INCOME_BAND_KEY } from '../../domain/presentation';
import { t, type PlainCopyKey } from '../../i18n/copy';
import { todayLocalIso } from '../../lib/now';
import { Button } from '../../ui/Button';
import { ChoiceChips, type ChoiceOption } from '../../ui/ChoiceChips';

/** Campo de C3 (Familia nueva y Agregar información). */
export type QuestionKey = C3AddInfoField;
/** Cualquier campo de Agregar información (C3 + booleanos de la propuesta fuera de C3). */
export type AddInfoQuestionKey = AddInfoField;
/** Respuesta cruda por pregunta: '' = sin responder; 'unknown' = "No sé". */
export type Answers = Readonly<Record<AddInfoQuestionKey, string>>;

export const UNKNOWN = 'unknown';
export const RSH_BANDS = [40, 50, 60, 70, 80, 90, 100] as const;
export const INCOME_BANDS: readonly IncomeBand[] = ['UNDER_110K', '110K_250K', '250K_400K', 'OVER_400K'];
export const HOUSING: readonly Exclude<HousingType, 'UNKNOWN'>[] = ['ADEQUATE', 'CAMP_OR_OCCUPATION', 'ROOM_IN_OTHER_HOME', 'OTHER'];

export const LABEL: Readonly<Record<C3AddInfoField, PlainCopyKey>> = {
  child_age: 'new_family.q.child_age',
  siblings_under_6: 'new_family.q.siblings_under_6',
  siblings_6_14: 'new_family.q.siblings_6_14',
  siblings_15_18: 'new_family.q.siblings_15_18',
  has_rsh: 'new_family.q.has_rsh',
  rsh_band: 'new_family.q.rsh_band',
  household_income_band: 'new_family.q.household_income_band',
  ssyo_participation: 'new_family.q.ssyo_participation',
  chile_crece_contigo_access: 'new_family.q.chile_crece_contigo_access',
  last_child_health_control_date: 'new_family.q.last_child_health_control_date',
  child_possible_disability: 'new_family.q.child_possible_disability',
  child_in_therapy: 'new_family.q.child_in_therapy',
  housing_type: 'new_family.q.housing_type',
  household_pregnancy: 'new_family.q.household_pregnancy',
  household_has_adult_over_65: 'new_family.q.household_has_adult_over_65',
  household_formal_employment_or_pension: 'new_family.q.household_formal_employment_or_pension',
  household_water_payment_difficulty: 'new_family.q.household_water_payment_difficulty',
  household_food_purchase_difficulty: 'new_family.q.household_food_purchase_difficulty',
};

/** Preguntas de los booleanos fuera de C3 ("Agregar información"; textos provisionales, PREG-070). */
const EXTRA_LABEL: Readonly<Record<AddInfoExtraField, string>> = {
  pregnancy_weeks_at_least_threshold: ADD_INFO_COPY.pregnancyWeeksMin,
  ...ADD_INFO_COPY.questions,
};

const isC3Field = (key: AddInfoQuestionKey): key is QuestionKey => Object.prototype.hasOwnProperty.call(LABEL, key);

/** Texto de la pregunta de un campo. */
export const questionLabel = (key: AddInfoQuestionKey): string => (isC3Field(key) ? t(LABEL[key]) : EXTRA_LABEL[key]);

export type Question<K extends AddInfoQuestionKey = QuestionKey> =
  | { readonly kind: 'count'; readonly key: K; readonly max: number }
  | { readonly kind: 'bool'; readonly key: K }
  | { readonly kind: 'choice'; readonly key: K; readonly options: () => ChoiceOption[] }
  | { readonly kind: 'date'; readonly key: K };

const count = <K extends AddInfoQuestionKey>(key: K, max: number): Question<K> => ({ kind: 'count', key, max });
const bool = <K extends AddInfoQuestionKey>(key: K): Question<K> => ({ kind: 'bool', key });

/** Una definición por campo cerrado (orden de la ficha). */
export const QUESTIONS: Readonly<Record<QuestionKey, Question>> = {
  child_age: count('child_age', 120),
  siblings_under_6: count('siblings_under_6', 30),
  siblings_6_14: count('siblings_6_14', 30),
  siblings_15_18: count('siblings_15_18', 30),
  has_rsh: bool('has_rsh'),
  rsh_band: {
    kind: 'choice',
    key: 'rsh_band',
    options: () => RSH_BANDS.map((band) => ({ value: String(band), label: t('new_family.rsh_band_option', { band: formatInteger(band) }) })),
  },
  household_income_band: {
    kind: 'choice',
    key: 'household_income_band',
    options: () => INCOME_BANDS.map((band) => ({ value: band, label: t(INCOME_BAND_KEY[band]) })),
  },
  ssyo_participation: bool('ssyo_participation'),
  chile_crece_contigo_access: bool('chile_crece_contigo_access'),
  last_child_health_control_date: { kind: 'date', key: 'last_child_health_control_date' },
  child_possible_disability: bool('child_possible_disability'),
  child_in_therapy: bool('child_in_therapy'),
  housing_type: { kind: 'choice', key: 'housing_type', options: () => HOUSING.map((h) => ({ value: h, label: t(HOUSING_KEY[h]) })) },
  household_pregnancy: bool('household_pregnancy'),
  household_has_adult_over_65: bool('household_has_adult_over_65'),
  household_formal_employment_or_pension: bool('household_formal_employment_or_pension'),
  household_water_payment_difficulty: bool('household_water_payment_difficulty'),
  household_food_purchase_difficulty: bool('household_food_purchase_difficulty'),
};

/** Booleanos fuera de C3: solo en "Agregar información" (nunca en Familia nueva). */
const EXTRA_QUESTIONS: Readonly<Record<AddInfoExtraField, Question<AddInfoExtraField>>> = {
  pregnancy_weeks_at_least_threshold: bool('pregnancy_weeks_at_least_threshold'),
  has_incompatible_coverage: bool('has_incompatible_coverage'),
  pregnancy_public_network_delivery: bool('pregnancy_public_network_delivery'),
  pregnancy_public_prenatal_control: bool('pregnancy_public_prenatal_control'),
  residence_requirement_met: bool('residence_requirement_met'),
  age_record_current: bool('age_record_current'),
};

/** Todas las preguntas de "Agregar información", en el orden de la ficha. */
export const ADD_INFO_QUESTIONS: Readonly<Record<AddInfoQuestionKey, Question<AddInfoQuestionKey>>> = { ...QUESTIONS, ...EXTRA_QUESTIONS };

export const QUESTION_ORDER = Object.keys(ADD_INFO_QUESTIONS) as AddInfoQuestionKey[];

export const EMPTY_ANSWERS = Object.fromEntries(QUESTION_ORDER.map((key) => [key, ''])) as Answers;

const boolOptions = (): ChoiceOption[] => [
  { value: 'yes', label: t('common.yes') },
  { value: 'no', label: t('common.no') },
];
const withUnknown = (options: ChoiceOption[]): ChoiceOption[] => [...options, { value: UNKNOWN, label: t('common.dont_know') }];

export const isFutureDate = (value: string): boolean => value !== '' && value > todayLocalIso();

/**
 * Valor C3 de una respuesta cruda (sin lógica de negocio): "No sé" → null, salvo vivienda → UNKNOWN.
 * '' (sin responder) también da null; quien arma el cuerpo decide si omite la clave.
 */
export function answerValue<K extends AddInfoQuestionKey>(key: K, raw: string): AddFamilyInfoRequestV1[K] {
  const question = ADD_INFO_QUESTIONS[key];
  let value: unknown = null;
  if (raw !== '' && raw !== UNKNOWN) {
    if (question.kind === 'count') value = Number(raw);
    else if (question.kind === 'bool') value = raw === 'yes' ? true : raw === 'no' ? false : null;
    else if (question.kind === 'date') value = raw;
    else if (key === 'rsh_band') value = RSH_BANDS.find((band) => String(band) === raw) ?? null;
    else if (key === 'household_income_band') value = INCOME_BANDS.find((band) => band === raw) ?? null;
    else if (key === 'housing_type') value = HOUSING.find((h) => h === raw) ?? null;
  } else if (raw === UNKNOWN && key === 'housing_type') {
    value = 'UNKNOWN';
  }
  return value as AddFamilyInfoRequestV1[K];
}

/** Texto de una respuesta para la revisión (solo etiquetas del catálogo). */
export function answerLabel(question: Question<AddInfoQuestionKey>, value: string): string {
  if (value === '') return t('common.unanswered');
  if (value === UNKNOWN) return t('common.dont_know');
  switch (question.kind) {
    case 'count':
      return formatInteger(Number(value));
    case 'bool':
      return value === 'yes' ? t('common.yes') : t('common.no');
    case 'date':
      return formatDate(value);
    case 'choice':
      return question.options().find((o) => o.value === value)?.label ?? t('common.unanswered');
  }
}

/** Reintento con la MISMA clave solo si la respuesta pudo perderse (red, timeout, 429, 5xx, 200 inválido). */
export function keepsIdempotencyKey(error: unknown): boolean {
  if (!isApiError(error)) return false;
  if (error.kind === 'network' || error.kind === 'timeout') return true;
  if (error.kind === 'http') return error.status === 429 || error.status >= 500;
  return isInvalidResponse(error);
}

export function QuestionField({
  question,
  value,
  onChange,
  label: labelOverride,
}: {
  readonly question: Question<AddInfoQuestionKey>;
  readonly value: string;
  readonly onChange: (value: string) => void;
  /** Texto que reemplaza la pregunta por defecto (p. ej. semanas con el umbral del motor). */
  readonly label?: string;
}) {
  const id = useId();
  const label = labelOverride ?? questionLabel(question.key);
  if (question.kind === 'count') {
    return (
      <div className="space-y-2">
        <label htmlFor={id} className="block font-semibold">
          {label}
        </label>
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-12 w-full rounded-xl border-2 border-border-strong bg-surface px-3 font-semibold"
        >
          <option value="">{t('common.unanswered')}</option>
          <option value={UNKNOWN}>{t('common.dont_know')}</option>
          {Array.from({ length: question.max + 1 }, (_, n) => (
            <option key={n} value={String(n)}>
              {formatInteger(n)}
            </option>
          ))}
        </select>
      </div>
    );
  }
  if (question.kind === 'date') {
    const future = isFutureDate(value);
    return (
      <div className="space-y-2">
        <label htmlFor={id} className="block font-semibold">
          {label}
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            id={id}
            type="date"
            value={value}
            max={todayLocalIso()}
            onChange={(event) => onChange(event.target.value)}
            aria-invalid={future || undefined}
            aria-describedby={future ? `${id}-error` : undefined}
            className="min-h-12 rounded-xl border-2 border-border-strong bg-surface px-3 font-semibold"
          />
          <Button variant="ghost" size="sm" onClick={() => onChange('')}>
            {t('common.dont_know')}
          </Button>
        </div>
        {future && (
          <p id={`${id}-error`} role="alert" className="font-semibold text-danger-ink">
            {t('new_family.date_future')}
          </p>
        )}
      </div>
    );
  }
  const options = question.kind === 'bool' ? boolOptions() : question.options();
  return <ChoiceChips legend={label} options={withUnknown(options)} value={value === '' ? null : value} onChange={onChange} />;
}
