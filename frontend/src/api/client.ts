// Cliente C3: una función por operationId (design.md §6.2). IDs de ruta validados con el patrón
// Id ANTES del request y codificados; cuerpos validados con su validador generado (sin request si
// no calzan). Las mutations NO reciben señal del llamador: solo sesión + timeout (NIT 8).
import { isValidId } from '../domain/ids';
import { formats } from './contract/runtime.js';
import { contractError } from './errors';
import {
  validateAssistantEnvelope,
  validateAssistantPublicRequest,
  validateConversationEnvelope,
  validateConversationRequest,
  validateFamiliaContextEnvelope,
  validateFamiliaDetailEnvelope,
  validateFamiliaListEnvelope,
  validateFamilyGenerationPublicRequest,
  validateFlyerDraftEnvelope,
  validateJardinListEnvelope,
  validateKpiEnvelope,
  validateMessageGenerationEnvelope,
  validateOpportunityListEnvelope,
  validatePreevaluationEnvelope,
  validatePreevaluationRequest,
  validateScriptGenerationEnvelope,
  validateTextractFlyerRequestV1,
  type ValidateFn,
} from './generated/validators.gen.js';
import { getTransport } from './transport';
import type {
  AssistantEnvelope,
  AssistantPublicRequest,
  C3Ok,
  ConversationEnvelope,
  ConversationRequest,
  FamiliaContextEnvelope,
  FamiliaDetailEnvelope,
  FamiliaListEnvelope,
  FamilyGenerationPublicRequest,
  FlyerDraftEnvelope,
  JardinListEnvelope,
  KpiEnvelope,
  KpiLevel,
  MessageGenerationEnvelope,
  OperationId,
  OpportunityListEnvelope,
  OpportunityOrder,
  PreevaluationEnvelope,
  PreevaluationRequest,
  ScriptGenerationEnvelope,
  TextractFlyerRequestV1,
} from './types';

/** Opciones de lectura: la señal del llamador solo existe en queries. */
export interface QueryOptions {
  readonly signal?: AbortSignal;
}

const READ_TIMEOUT_MS = 15_000;
const GENERATION_TIMEOUT_MS = 30_000;
/** NIT 9: máximo de C3; Demo tiene 50 jardines, así cabe todo en una página. */
export const JARDINES_PAGE_LIMIT = 100;
const MAX_CURSOR_LENGTH = 2048;
const ORDERS: readonly OpportunityOrder[] = ['prioridad', 'urgencia', 'beneficio'];
const KPI_LEVELS: readonly KpiLevel[] = ['jardin', 'comuna', 'region', 'nacional'];

/** Timeouts de la tabla §6.2 (exportados para pruebas). */
export const OPERATION_TIMEOUTS: Readonly<Record<OperationId, number>> = {
  listJardines: READ_TIMEOUT_MS,
  listFamiliasByJardin: READ_TIMEOUT_MS,
  getFamilia: READ_TIMEOUT_MS,
  getContextoFamilia: READ_TIMEOUT_MS,
  listOportunidades: READ_TIMEOUT_MS,
  createGuion: GENERATION_TIMEOUT_MS,
  createMensaje: GENERATION_TIMEOUT_MS,
  createConversacion: READ_TIMEOUT_MS,
  createPreevaluacion: GENERATION_TIMEOUT_MS,
  getKpi: READ_TIMEOUT_MS,
  askCatalogAssistant: GENERATION_TIMEOUT_MS,
  ingestSyntheticFlyer: GENERATION_TIMEOUT_MS,
};

function requireId(operationId: OperationId, value: unknown): string {
  if (!isValidId(value)) throw contractError(operationId, 'invalid_param');
  return encodeURIComponent(value);
}

function requireBody<T>(operationId: OperationId, validate: ValidateFn<T>, body: unknown): T {
  if (!validate(body)) throw contractError(operationId, 'invalid_param');
  return body;
}

function requireIdempotencyKey(operationId: OperationId, key: unknown): string {
  if (typeof key !== 'string' || !formats.uuid(key)) throw contractError(operationId, 'invalid_param');
  return key;
}

function cursorQuery(operationId: OperationId, cursor: string | undefined): Record<string, string> {
  if (cursor === undefined) return {};
  if (typeof cursor !== 'string' || cursor.length === 0 || cursor.length > MAX_CURSOR_LENGTH) {
    throw contractError(operationId, 'invalid_param');
  }
  return { cursor };
}

function get<T>(
  operationId: OperationId,
  path: string,
  route: string,
  validate: ValidateFn<T>,
  opts: QueryOptions,
  query?: Record<string, string>,
): Promise<C3Ok<T>> {
  return getTransport().send({
    operationId,
    method: 'GET',
    path,
    route,
    query,
    expectedStatus: 200,
    validate,
    timeoutMs: OPERATION_TIMEOUTS[operationId],
    signal: opts.signal,
  });
}

function post<T>(
  operationId: OperationId,
  path: string,
  route: string,
  body: unknown,
  validate: ValidateFn<T>,
  expectedStatus: 200 | 201,
  headers?: Record<string, string>,
): Promise<C3Ok<T>> {
  // Sin `signal` del llamador (NIT 8): desmontar la vista no aborta el POST.
  return getTransport().send({
    operationId,
    method: 'POST',
    path,
    route,
    body,
    headers,
    expectedStatus,
    validate,
    timeoutMs: OPERATION_TIMEOUTS[operationId],
  });
}

// Las funciones son async para que un parámetro inválido rechace la promesa (nunca lanza sincrónico).

export async function listJardines(params: { cursor?: string } = {}, opts: QueryOptions = {}): Promise<C3Ok<JardinListEnvelope>> {
  const query = { limit: String(JARDINES_PAGE_LIMIT), ...cursorQuery('listJardines', params.cursor) };
  return get('listJardines', '/jardines', '/jardines', validateJardinListEnvelope, opts, query);
}

export async function listFamiliasByJardin(
  params: { gardenId: string; cursor?: string },
  opts: QueryOptions = {},
): Promise<C3Ok<FamiliaListEnvelope>> {
  const id = requireId('listFamiliasByJardin', params.gardenId);
  const query = cursorQuery('listFamiliasByJardin', params.cursor);
  return get('listFamiliasByJardin', `/jardines/${id}/familias`, '/jardines/{id}/familias', validateFamiliaListEnvelope, opts, query);
}

export async function getFamilia(params: { familyId: string }, opts: QueryOptions = {}): Promise<C3Ok<FamiliaDetailEnvelope>> {
  const id = requireId('getFamilia', params.familyId);
  return get('getFamilia', `/familias/${id}`, '/familias/{id}', validateFamiliaDetailEnvelope, opts);
}

export async function getContextoFamilia(
  params: { familyId: string },
  opts: QueryOptions = {},
): Promise<C3Ok<FamiliaContextEnvelope>> {
  const id = requireId('getContextoFamilia', params.familyId);
  return get('getContextoFamilia', `/familias/${id}/contexto`, '/familias/{id}/contexto', validateFamiliaContextEnvelope, opts);
}

export async function listOportunidades(
  params: { familyId: string; orden?: OpportunityOrder },
  opts: QueryOptions = {},
): Promise<C3Ok<OpportunityListEnvelope>> {
  const id = requireId('listOportunidades', params.familyId);
  const orden = params.orden ?? 'prioridad';
  if (!ORDERS.includes(orden)) throw contractError('listOportunidades', 'invalid_param');
  return get(
    'listOportunidades',
    `/familias/${id}/oportunidades`,
    '/familias/{id}/oportunidades',
    validateOpportunityListEnvelope,
    opts,
    { orden },
  );
}

export async function createGuion(params: {
  familyId: string;
  body: FamilyGenerationPublicRequest;
}): Promise<C3Ok<ScriptGenerationEnvelope>> {
  const id = requireId('createGuion', params.familyId);
  const body = requireBody('createGuion', validateFamilyGenerationPublicRequest, params.body);
  return post('createGuion', `/familias/${id}/guion`, '/familias/{id}/guion', body, validateScriptGenerationEnvelope, 200);
}

export async function createMensaje(params: {
  familyId: string;
  body: FamilyGenerationPublicRequest;
}): Promise<C3Ok<MessageGenerationEnvelope>> {
  const id = requireId('createMensaje', params.familyId);
  const body = requireBody('createMensaje', validateFamilyGenerationPublicRequest, params.body);
  return post('createMensaje', `/familias/${id}/mensaje`, '/familias/{id}/mensaje', body, validateMessageGenerationEnvelope, 200);
}

export async function createConversacion(params: {
  familyId: string;
  body: ConversationRequest;
  idempotencyKey: string;
}): Promise<C3Ok<ConversationEnvelope>> {
  const id = requireId('createConversacion', params.familyId);
  const body = requireBody('createConversacion', validateConversationRequest, params.body);
  const key = requireIdempotencyKey('createConversacion', params.idempotencyKey);
  return post(
    'createConversacion',
    `/familias/${id}/conversaciones`,
    '/familias/{id}/conversaciones',
    body,
    validateConversationEnvelope,
    201,
    { 'Idempotency-Key': key },
  );
}

export async function createPreevaluacion(params: {
  body: PreevaluationRequest;
  idempotencyKey: string;
}): Promise<C3Ok<PreevaluationEnvelope>> {
  const body = requireBody('createPreevaluacion', validatePreevaluationRequest, params.body);
  const key = requireIdempotencyKey('createPreevaluacion', params.idempotencyKey);
  return post(
    'createPreevaluacion',
    '/familias/nueva/preevaluacion',
    '/familias/nueva/preevaluacion',
    body,
    validatePreevaluationEnvelope,
    200,
    { 'Idempotency-Key': key },
  );
}

export interface KpiParams {
  readonly nivel: KpiLevel;
  readonly id?: string;
  readonly desde?: string;
  readonly hasta?: string;
}

export async function getKpi(params: KpiParams, opts: QueryOptions = {}): Promise<C3Ok<KpiEnvelope>> {
  if (!KPI_LEVELS.includes(params.nivel)) throw contractError('getKpi', 'invalid_param');
  const query: Record<string, string> = { nivel: params.nivel };
  if (params.id !== undefined) {
    if (!isValidId(params.id)) throw contractError('getKpi', 'invalid_param');
    query.id = params.id;
  }
  for (const key of ['desde', 'hasta'] as const) {
    const value = params[key];
    if (value === undefined) continue;
    if (!formats.date(value)) throw contractError('getKpi', 'invalid_param');
    query[key] = value;
  }
  return get('getKpi', '/kpi', '/kpi', validateKpiEnvelope, opts, query);
}

export async function askCatalogAssistant(params: { body: AssistantPublicRequest }): Promise<C3Ok<AssistantEnvelope>> {
  const body = requireBody('askCatalogAssistant', validateAssistantPublicRequest, params.body);
  return post('askCatalogAssistant', '/asistente', '/asistente', body, validateAssistantEnvelope, 200);
}

/** Operación 12 (FE-T07 sin UI): solo metadatos de un asset sintético inventariado. */
export async function ingestSyntheticFlyer(params: { body: TextractFlyerRequestV1 }): Promise<C3Ok<FlyerDraftEnvelope>> {
  const body = requireBody('ingestSyntheticFlyer', validateTextractFlyerRequestV1, params.body);
  return post('ingestSyntheticFlyer', '/catalogo/ingesta-afiche', '/catalogo/ingesta-afiche', body, validateFlyerDraftEnvelope, 200);
}
