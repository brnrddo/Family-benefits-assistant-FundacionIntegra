// Cliente de la operación PROPUESTA `addFamiliaAntecedentes` (DEC-039, PREG-039): POST
// /familias/{id}/antecedentes. Vive FUERA del cliente generado desde C3 (src/api/client.ts) para que
// nadie la confunda con el contrato vigente; usa el mismo transporte (sesión, timeout, algoritmo de
// respuesta) y valida request (schema local) y respuesta (FamiliaDetailEnvelope de C3). Solo se usa
// si `capabilities.addInfo` (mocks por defecto; API real solo con VITE_PROPOSAL_ADD_INFO=true).
// Propuesta para Rol 2: frontend/docs/PROPUESTA_C3_agregar_informacion.md.
import { isValidId } from '../../domain/ids';
import { formats } from '../contract/runtime.js';
import { contractError } from '../errors';
import { validateFamiliaDetailEnvelope } from '../generated/validators.gen.js';
import { getTransport } from '../transport';
import type { C3Ok, FamiliaDetailEnvelope, ProposalOperationId } from '../types';
import { validateAddFamilyInfoRequestV1 } from './generated/validators.gen.js';
import type { AddFamilyInfoRequestV1, AddInfoField } from './types';

export const ADD_INFO_OPERATION_ID: ProposalOperationId = 'addFamiliaAntecedentes';
export const ADD_INFO_ROUTE = '/familias/{id}/antecedentes';
const ADD_INFO_TIMEOUT_MS = 30_000;

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

/** Umbral de semanas de embarazo (parámetro público del motor) recibido en la última respuesta; null = sin dato. */
let weeksThreshold: number | null = null;

export function pregnancyWeeksThreshold(): number | null {
  return weeksThreshold;
}

const THRESHOLD_KEY = 'pregnancy_weeks_threshold';

/**
 * La respuesta puede traer `pregnancy_weeks_threshold` (entero 1–45, fuera de C3). Se valida, se quita
 * del cuerpo y el resto se valida como FamiliaDetailEnvelope de C3 (cerrado).
 */
export const validateAddInfoResponse = Object.assign(
  (data: unknown): data is FamiliaDetailEnvelope => {
    let threshold: number | null = null;
    if (data !== null && typeof data === 'object' && Object.prototype.hasOwnProperty.call(data, THRESHOLD_KEY)) {
      const raw = (data as Record<string, unknown>)[THRESHOLD_KEY];
      if (typeof raw !== 'number' || !Number.isInteger(raw) || raw < 1 || raw > 45) {
        validateAddInfoResponse.errors = [{ instancePath: `/${THRESHOLD_KEY}`, keyword: 'type' }];
        return false;
      }
      threshold = raw;
      delete (data as Record<string, unknown>)[THRESHOLD_KEY];
    }
    const ok = validateFamiliaDetailEnvelope(data);
    validateAddInfoResponse.errors = validateFamiliaDetailEnvelope.errors ?? null;
    if (ok && threshold !== null) weeksThreshold = threshold;
    return ok;
  },
  { errors: null as { instancePath: string; keyword: string }[] | null },
);

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
    validate: validateAddInfoResponse,
    timeoutMs: ADD_INFO_TIMEOUT_MS,
  });
}
