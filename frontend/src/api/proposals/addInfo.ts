// Cliente de la operación PROPUESTA `addFamiliaAntecedentes` (DEC-039, PREG-039): POST
// /familias/{id}/antecedentes, y su GET previo (umbral N de semanas, solo si se pregunta embarazo). Vive FUERA del cliente generado desde C3 (src/api/client.ts) para que
// nadie la confunda con el contrato vigente; usa el mismo transporte (sesión, timeout, algoritmo de
// respuesta) y valida request (schema local) y respuesta (FamiliaDetailEnvelope de C3). Solo se usa
// si `capabilities.addInfo` (mocks por defecto; API real solo con VITE_PROPOSAL_ADD_INFO=true).
// Propuesta para Rol 2: frontend/docs/PROPUESTA_C3_agregar_informacion.md.
import { isValidId } from '../../domain/ids';
import { formats } from '../contract/runtime.js';
import { contractError } from '../errors';
import { validateFamiliaDetailEnvelope } from '../generated/validators.gen.js';
import { getTransport } from '../transport';
import type { C3Ok, EnvelopeMetadata, FamiliaDetailEnvelope, ProposalOperationId } from '../types';
import { validateAddFamilyInfoRequestV1 } from './generated/validators.gen.js';
import { ADD_INFO_EXTRA_FIELDS, type AddFamilyInfoRequestV1, type AddInfoField } from './types';

export const ADD_INFO_OPERATION_ID: ProposalOperationId = 'addFamiliaAntecedentes';
export const ADD_INFO_ROUTE = '/familias/{id}/antecedentes';
const ADD_INFO_TIMEOUT_MS = 30_000;
const ANTECEDENTES_TIMEOUT_MS = 15_000;

/**
 * `missing_code` → UN campo de la propuesta: enum de C3 FamilyContextView → campo de
 * PreevaluationRequest; códigos del motor (C3 BenefitResult admite cualquier `^[a-z0-9_.-]+$`) →
 * campo C3 equivalente o booleano de la propuesta fuera de C3. `residencia_*` se resuelve por prefijo
 * en `fieldForMissingCode`. `composition` y los códigos que no estén aquí no tienen campo cerrado: la
 * UI los muestra solo como guía (DEC-039).
 */
export const MISSING_CODE_FIELD: Readonly<Partial<Record<string, AddInfoField>>> = {
  child_age: 'child_age',
  siblings_under_6: 'siblings_under_6',
  siblings_6_14: 'siblings_6_14',
  siblings_15_18: 'siblings_15_18',
  rsh_status: 'has_rsh',
  rsh_band: 'rsh_band',
  income_band: 'household_income_band',
  ssyo_participation: 'ssyo_participation',
  chile_crece_contigo_access: 'chile_crece_contigo_access',
  last_health_control_date: 'last_child_health_control_date',
  possible_disability: 'child_possible_disability',
  therapy: 'child_in_therapy',
  housing_type: 'housing_type',
  pregnancy: 'household_pregnancy',
  adult_over_65: 'household_has_adult_over_65',
  employment_or_pension: 'household_formal_employment_or_pension',
  water_difficulty: 'household_water_payment_difficulty',
  food_difficulty: 'household_food_purchase_difficulty',
  // Códigos del motor (.agents/tasks/arreglos-ficha/codigos-motor.md).
  semanas_gestacion: 'household_pregnancy',
  cobertura_incompatible: 'has_incompatible_coverage',
  parto_red_publica: 'pregnancy_public_network_delivery',
  control_prenatal_red_publica: 'pregnancy_public_prenatal_control',
  antecedente_edad_vigente: 'age_record_current',
  tramo_rsh: 'rsh_band',
};

const RESIDENCE_PREFIX = 'residencia_';

export function fieldForMissingCode(code: string): AddInfoField | null {
  if (Object.prototype.hasOwnProperty.call(MISSING_CODE_FIELD, code)) return MISSING_CODE_FIELD[code] ?? null;
  return code.startsWith(RESIDENCE_PREFIX) ? 'residence_requirement_met' : null;
}

/** Campo que solo se pregunta si el campo padre se respondió "Sí" (semanas tras "¿Hay alguien embarazada?"). */
export const DEPENDENT_FIELDS: Readonly<Partial<Record<AddInfoField, readonly AddInfoField[]>>> = {
  household_pregnancy: ['pregnancy_weeks_at_least_threshold'],
};

/** GET /familias/{id}/antecedentes: datos que la pantalla necesita ANTES de preguntar (fuera de C3). */
export interface AntecedentesEnvelope {
  readonly meta: EnvelopeMetadata;
  readonly data: {
    readonly family_id: string;
    readonly pregnancy_weeks_threshold: number;
    /** Campos ya declarados (solo nombres, nunca valores; DEC-093). Opcional: un backend sin el cambio sigue validando. */
    readonly declared_fields?: readonly string[];
  };
}

const DECLARED_FIELD_PATTERN = /^[a-z0-9_]+$/;
const MAX_DECLARED_FIELDS = 40;

const isDeclaredFields = (value: unknown): boolean =>
  Array.isArray(value) &&
  value.length <= MAX_DECLARED_FIELDS &&
  value.every((item) => typeof item === 'string' && DECLARED_FIELD_PATTERN.test(item));

const META_KEYS = ['request_id', 'snapshot_id', 'eligibility_bundle_hash', 'content_bundle_hash', 'content_version'];
const isRecord = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value);
const hasExactKeys = (value: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(value).length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));

/**
 * Envelope cerrado: `meta` de C3 (mismas claves, strings) y `data` con solo `family_id`, el umbral N
 * de semanas (entero 1–45, parámetro público del motor P006-02) y, opcional, `declared_fields`
 * (nombres de campo `^[a-z0-9_]+$`, ≤ 40). Cualquier otra forma se rechaza.
 */
export const validateAntecedentesEnvelope = Object.assign(
  (value: unknown): value is AntecedentesEnvelope => {
    const ok =
      isRecord(value) &&
      hasExactKeys(value, ['meta', 'data']) &&
      isRecord(value.meta) &&
      hasExactKeys(value.meta, META_KEYS) &&
      META_KEYS.every((key) => typeof (value.meta as Record<string, unknown>)[key] === 'string') &&
      isRecord(value.data) &&
      (hasExactKeys(value.data, ['family_id', 'pregnancy_weeks_threshold']) ||
        (hasExactKeys(value.data, ['family_id', 'pregnancy_weeks_threshold', 'declared_fields']) && isDeclaredFields(value.data.declared_fields))) &&
      isValidId(value.data.family_id) &&
      Number.isInteger(value.data.pregnancy_weeks_threshold) &&
      (value.data.pregnancy_weeks_threshold as number) >= 1 &&
      (value.data.pregnancy_weeks_threshold as number) <= 45;
    validateAntecedentesEnvelope.errors = ok ? null : [{ instancePath: '', keyword: 'type' }];
    return ok;
  },
  { errors: null as { instancePath: string; keyword: string }[] | null },
);

const KNOWN_FIELDS: ReadonlySet<string> = new Set<AddInfoField>([
  ...Object.values(MISSING_CODE_FIELD).filter((field): field is AddInfoField => field !== undefined),
  ...ADD_INFO_EXTRA_FIELDS,
]);

/** Campos ya declarados del envelope, filtrados a campos conocidos de la pantalla (desconocidos se ignoran). */
export function declaredFieldsOf(envelope: AntecedentesEnvelope | undefined): ReadonlySet<AddInfoField> {
  const fields = envelope?.data.declared_fields ?? [];
  return new Set(fields.filter((field): field is AddInfoField => KNOWN_FIELDS.has(field)));
}

/** Umbral N de semanas de embarazo para la pregunta "¿Tiene N semanas o más?" (mismo recurso propuesto). */
export async function getFamiliaAntecedentes(params: { familyId: string; signal?: AbortSignal }): Promise<C3Ok<AntecedentesEnvelope>> {
  const op = ADD_INFO_OPERATION_ID;
  if (!isValidId(params.familyId)) throw contractError(op, 'invalid_param');
  const id = encodeURIComponent(params.familyId);
  return getTransport().send({
    operationId: op,
    method: 'GET',
    path: `/familias/${id}/antecedentes`,
    route: ADD_INFO_ROUTE,
    expectedStatus: 200,
    validate: validateAntecedentesEnvelope,
    timeoutMs: ANTECEDENTES_TIMEOUT_MS,
    ...(params.signal !== undefined ? { signal: params.signal } : {}),
  });
}

export async function addFamiliaAntecedentes(params: {
  familyId: string;
  body: AddFamilyInfoRequestV1;
  idempotencyKey: string;
}): Promise<C3Ok<FamiliaDetailEnvelope>> {
  const op = ADD_INFO_OPERATION_ID;
  if (!isValidId(params.familyId)) throw contractError(op, 'invalid_param');
  if (!validateAddFamilyInfoRequestV1(params.body)) throw contractError(op, 'invalid_param');
  if (typeof params.idempotencyKey !== 'string' || !formats.uuid(params.idempotencyKey)) throw contractError(op, 'invalid_param');
  const id = encodeURIComponent(params.familyId);
  // Sin `signal` del llamador (igual que las mutations C3): salir de la vista no aborta el POST.
  return getTransport().send({
    operationId: op,
    method: 'POST',
    path: `/familias/${id}/antecedentes`,
    route: ADD_INFO_ROUTE,
    body: params.body,
    headers: { 'Idempotency-Key': params.idempotencyKey },
    expectedStatus: 200,
    validate: validateFamiliaDetailEnvelope,
    timeoutMs: ADD_INFO_TIMEOUT_MS,
  });
}
