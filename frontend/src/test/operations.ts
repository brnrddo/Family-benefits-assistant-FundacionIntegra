// Las 12 operaciones C3 con parámetros sintéticos válidos (para pruebas de contrato y equivalencia).
import { http, type HttpHandler } from 'msw';
import * as client from '../api/client';
import meta from '../api/generated/c3.meta.json';
import type { C3Ok, OperationId } from '../api/types';
import { conversationRequest, preevaluationRequest } from './fixtures';

/** UUID v4 fijo para que las dos corridas de una prueba usen la misma clave. */
export const TEST_IDEMPOTENCY_KEY = '3f6c1a2e-8b4d-4c1e-9a7f-2d5e6b7c8d9e';

export const OPERATION_CALLS: Readonly<Record<OperationId, () => Promise<C3Ok<unknown>>>> = {
  listJardines: () => client.listJardines(),
  listFamiliasByJardin: () => client.listFamiliasByJardin({ gardenId: 'JAR-SIM-E3-00001' }),
  getFamilia: () => client.getFamilia({ familyId: 'FAM-SIM-E3-00001' }),
  getContextoFamilia: () => client.getContextoFamilia({ familyId: 'FAM-SIM-E3-00002' }),
  listOportunidades: () => client.listOportunidades({ familyId: 'FAM-SIM-E3-00001', orden: 'urgencia' }),
  createGuion: () => client.createGuion({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001', 'BEN-002', 'BEN-003'] } }),
  createMensaje: () => client.createMensaje({ familyId: 'FAM-SIM-E3-00001', body: { benefit_ids: ['BEN-001', 'BEN-002', 'BEN-003'] } }),
  createConversacion: () =>
    client.createConversacion({ familyId: 'FAM-SIM-E3-00001', body: conversationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY }),
  createPreevaluacion: () => client.createPreevaluacion({ body: preevaluationRequest(), idempotencyKey: TEST_IDEMPOTENCY_KEY }),
  getKpi: () => client.getKpi({ nivel: 'jardin', id: 'JAR-SIM-E3-00001' }),
  askCatalogAssistant: () => client.askCatalogAssistant({ body: { question: '¿Qué apoyos existen para niños en jardín infantil?' } }),
  ingestSyntheticFlyer: () =>
    client.ingestSyntheticFlyer({ body: { synthetic_asset_id: 'ASSET-SIM-001', media_type: 'image/png', sha256: 'a'.repeat(64) } }),
};

export const OPERATION_IDS = Object.keys(OPERATION_CALLS) as OperationId[];

type Resolver = Parameters<typeof http.get>[1];

/** Handler MSW que reemplaza la respuesta de una operación (para `server.use`). */
export function overrideOperation(operationId: OperationId, resolver: Resolver): HttpHandler {
  const op = (meta.operations as Record<string, { method: string; path: string }>)[operationId];
  if (op === undefined) throw new Error(`op_desconocida:${operationId}`);
  const pattern = `*/api/v1${op.path.replace('{id}', ':id')}`;
  return op.method === 'GET' ? http.get(pattern, resolver) : http.post(pattern, resolver);
}

export function expectedStatusOf(operationId: OperationId): number {
  return (meta.operations as Record<string, { expectedStatus: number }>)[operationId]?.expectedStatus ?? 200;
}
