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
import type { C3Ok, FamiliaDetailEnvelope, MissingCode, ProposalOperationId } from '../types';
import { validateAddFamilyInfoRequestV1 } from './generated/validators.gen.js';
import type { AddFamilyInfoRequestV1, AddInfoField } from './types';

export const ADD_INFO_OPERATION_ID: ProposalOperationId = 'addFamiliaAntecedentes';
export const ADD_INFO_ROUTE = '/familias/{id}/antecedentes';
const ADD_INFO_TIMEOUT_MS = 30_000;

/**
 * `missing_code` (enum de C3 FamilyContextView) → campo cerrado equivalente de PreevaluationRequest.
 * `composition` no tiene campo cerrado: la UI muestra la pregunta sugerida de C3 solo como guía (DEC-039).
 * Un código que no esté aquí (C3 BenefitResult admite cualquier `^[a-z0-9_.-]+$`) tampoco tiene campo.
 */
export const MISSING_CODE_FIELD: Readonly<Partial<Record<MissingCode, AddInfoField>>> = {
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
};

export function fieldForMissingCode(code: string): AddInfoField | null {
  return Object.prototype.hasOwnProperty.call(MISSING_CODE_FIELD, code) ? (MISSING_CODE_FIELD[code as MissingCode] ?? null) : null;
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
