// Cliente de la operación PROPUESTA `getCatalogoAlcance` (DEC-072, fuera de C3 v1.0.2): GET
// /catalogo/alcance → alcance NACIONAL/LOCAL por beneficio, título y marca "solo demo". Vive FUERA
// del cliente generado desde C3 (src/api/client.ts), con el mismo transporte, y valida la respuesta
// con el schema cerrado local. Solo se usa si `capabilities.territorial` (mocks por defecto; API real
// solo con VITE_PROPOSAL_TERRITORIAL=true). Propuesta del servidor: backend/app/api/PROPUESTA_ALCANCE.md.
import { getTransport } from '../transport';
import type { C3Ok, ProposalOperationId } from '../types';
import { validateCatalogScopeEnvelopeV1 } from './generated/validators.gen.js';
import type { CatalogScopeEnvelopeV1 } from './types';

export const TERRITORIAL_OPERATION_ID: ProposalOperationId = 'getCatalogoAlcance';
export const TERRITORIAL_ROUTE = '/catalogo/alcance';
const TERRITORIAL_TIMEOUT_MS = 15_000;

/**
 * PROVISIONAL: excepción documentada a FE-004; el catálogo i18n está congelado en 407 claves; Rol 4
 * debe pasarlo a content/i18n/es.json (PREG-070).
 */
export const TERRITORIAL_COPY = {
  localChip: 'Disponible en su comuna',
  demoLabel: 'Solo demo',
} as const;

export async function getCatalogoAlcance(opts: { signal?: AbortSignal } = {}): Promise<C3Ok<CatalogScopeEnvelopeV1>> {
  return getTransport().send({
    operationId: TERRITORIAL_OPERATION_ID,
    method: 'GET',
    path: TERRITORIAL_ROUTE,
    route: TERRITORIAL_ROUTE,
    expectedStatus: 200,
    validate: validateCatalogScopeEnvelopeV1,
    timeoutMs: TERRITORIAL_TIMEOUT_MS,
    ...(opts.signal !== undefined ? { signal: opts.signal } : {}),
  });
}
