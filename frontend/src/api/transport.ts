// Transporte C3 (design.md §6.2–§6.3). Puerta de sesión ANTES de fetch, opciones fetch cerradas,
// timeouts por operación y algoritmo normativo de respuesta (pasos 1–4). El transporte mock
// (src/mocks/transport.ts) reutiliza este mismo núcleo con otro `dispatch`.
// Las vistas nunca importan este módulo (§4.1; lo impide el lint).
import { anySignal, timeoutSignal } from '../lib/abort';
import { discardBody, MAX_ERROR_BODY_BYTES, MAX_SUCCESS_BODY_BYTES, readBodyText } from '../lib/bodyReader';
import { log } from '../lib/log';
import { now, nowMs } from '../lib/now';
import type { SessionPort } from '../auth/session';
import { ApiError, contractError, isApiError, RETRYABLE_STATUSES } from './errors';
import { validateErrorResponse, type ValidateFn } from './generated/validators.gen.js';
import type { C3Ok, OperationId } from './types';

export interface TransportRequest<T> {
  readonly operationId: OperationId;
  readonly method: 'GET' | 'POST';
  /** Path relativo a la base, con IDs ya validados y codificados (p. ej. `/familias/FAM-SIM-E3-00001`). */
  readonly path: string;
  /** Ruta normalizada para logs (p. ej. `/familias/{id}`); nunca lleva IDs. */
  readonly route: string;
  readonly query?: Readonly<Record<string, string>>;
  /** Cuerpo ya validado con su validador de request. */
  readonly body?: unknown;
  readonly headers?: Readonly<Record<string, string>>;
  /** 201 en createConversacion, 200 en el resto. */
  readonly expectedStatus: number;
  readonly validate: ValidateFn<T>;
  readonly timeoutMs: number;
  /** Señal del llamador: solo queries (las mutations no la reciben, NIT 8). */
  readonly signal?: AbortSignal;
}

export interface Transport {
  send<T>(request: TransportRequest<T>): Promise<C3Ok<T>>;
}

/** Ejecuta el `Request` ya armado: `fetch` real o `getResponse` de MSW en proceso. */
export type Dispatch = (request: Request, operationId: OperationId) => Promise<Response>;

export interface TransportDeps {
  /** Base absoluta terminada en /api/v1 (sin barra final). */
  readonly baseUrl: string;
  readonly session: SessionPort;
}

function buildUrl(baseUrl: string, path: string, query: Readonly<Record<string, string>> | undefined): string {
  const url = new URL(`${baseUrl.replace(/\/$/, '')}${path}`);
  if (query !== undefined) {
    for (const [key, value] of Object.entries(query)) url.searchParams.set(key, value);
  }
  return url.href;
}

function mediaTypeOf(response: Response): string {
  return (response.headers.get('content-type') ?? '').split(';')[0]?.trim().toLowerCase() ?? '';
}

function requestIdOf(body: unknown): string | null {
  if (body === null || typeof body !== 'object') return null;
  const meta = (body as { meta?: { request_id?: unknown } }).meta;
  if (meta !== undefined && typeof meta.request_id === 'string') return meta.request_id;
  const direct = (body as { request_id?: unknown }).request_id;
  return typeof direct === 'string' ? direct : null;
}

/** Algoritmo normativo de la respuesta (§6.2, pasos 1–4). */
export async function interpretResponse<T>(response: Response, request: TransportRequest<T>): Promise<C3Ok<T>> {
  const op = request.operationId;
  // 4) La API nunca redirige: seguirla podría terminar en HTML de login o en otro origen.
  if (response.type === 'opaqueredirect') throw contractError(op, 'unexpected_status', { status: 0 });
  const status = response.status;

  // 1) Status esperado: media type, tamaño, UTF-8 estricto y validador del envelope.
  if (status === request.expectedStatus) {
    if (mediaTypeOf(response) !== 'application/json') {
      await discardBody(response);
      throw contractError(op, 'content_type', { status });
    }
    const declared = response.headers.get('content-length');
    if (declared !== null && /^\d+$/.test(declared.trim()) && Number(declared) > MAX_SUCCESS_BODY_BYTES) {
      await discardBody(response);
      throw contractError(op, 'too_large', { status });
    }
    const read = await readBodyText(response, MAX_SUCCESS_BODY_BYTES);
    if (!read.ok) throw contractError(op, read.reason, { status });
    let data: unknown;
    try {
      data = JSON.parse(read.text);
    } catch {
      throw contractError(op, 'schema', { status, instancePath: '', keyword: 'json' });
    }
    if (!request.validate(data)) {
      const first = request.validate.errors?.[0];
      throw contractError(op, 'schema', { status, instancePath: first?.instancePath ?? '', keyword: first?.keyword ?? '' });
    }
    return { status, body: data, requestId: requestIdOf(data), receivedAt: now().toISOString() };
  }

  // 2) Cualquier no-2xx: la clasificación depende solo del status; un cuerpo de error nunca da ContractError.
  if (status < 200 || status > 299) {
    let code = 'UNKNOWN';
    let requestId: string | null = null;
    let retryable = RETRYABLE_STATUSES.has(status);
    const read = await readBodyText(response, MAX_ERROR_BODY_BYTES);
    if (read.ok && mediaTypeOf(response) === 'application/json') {
      try {
        const parsed: unknown = JSON.parse(read.text);
        if (validateErrorResponse(parsed)) {
          code = parsed.error.code;
          requestId = parsed.error.request_id;
          retryable = parsed.error.retryable;
        }
      } catch {
        // HTML de WAF/CloudFront o {"message": …} de API Gateway: se queda en UNKNOWN
      }
    }
    throw new ApiError({ kind: 'http', status, code, requestId, retryable });
  }

  // 3) 2xx distinto del esperado (200 en createConversacion, 202, 204…).
  await discardBody(response);
  throw contractError(op, 'unexpected_status', { status });
}

interface SignalSet {
  readonly timeout: AbortSignal;
  readonly session: AbortSignal;
  readonly caller: AbortSignal | undefined;
}

/** Clasifica una falla por la señal que disparó: timeout → timeout; sesión/llamador → cancelled. */
function classify(error: unknown, signals: SignalSet): ApiError {
  if (isApiError(error)) return error;
  if (signals.timeout.aborted) return new ApiError({ kind: 'timeout' });
  if (signals.session.aborted) return new ApiError({ kind: 'cancelled', cause: 'session' });
  if (signals.caller?.aborted === true) return new ApiError({ kind: 'cancelled', cause: 'caller' });
  // TypeError de fetch (incluye CORS bloqueado: el status no es legible) → network.
  return new ApiError({ kind: 'network' });
}

export function createTransport(deps: TransportDeps & { readonly dispatch: Dispatch }): Transport {
  const { baseUrl, session, dispatch } = deps;
  return {
    async send<T>(request: TransportRequest<T>): Promise<C3Ok<T>> {
      const started = nowMs();
      // Puerta de sesión: sin sesión válida no se emite el request (nunca un request cloud sin Authorization).
      const decision = session.getAccessToken();
      if (decision.kind === 'denied') throw new ApiError({ kind: 'auth_required' });
      const sessionSignal = session.signal();
      if (sessionSignal.aborted) throw new ApiError({ kind: 'cancelled', cause: 'session' });
      if (request.signal?.aborted === true) throw new ApiError({ kind: 'cancelled', cause: 'caller' });

      const timeout = timeoutSignal(request.timeoutMs);
      const signal = anySignal([request.signal, sessionSignal, timeout.signal]);
      const headers = new Headers({ Accept: 'application/json' });
      if (request.body !== undefined) headers.set('Content-Type', 'application/json');
      for (const [name, value] of Object.entries(request.headers ?? {})) headers.set(name, value);
      if (decision.kind === 'bearer') headers.set('Authorization', `Bearer ${decision.token}`);

      const fetchRequest = new Request(buildUrl(baseUrl, request.path, request.query), {
        method: request.method,
        headers,
        body: request.body === undefined ? undefined : JSON.stringify(request.body),
        credentials: 'omit',
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
        redirect: 'manual',
        signal,
      });

      try {
        const response = await dispatch(fetchRequest, request.operationId);
        return await interpretResponse(response, request);
      } catch (error) {
        const apiError = classify(error, { timeout: timeout.signal, session: sessionSignal, caller: request.signal });
        if (apiError.kind !== 'cancelled') {
          log.warn({
            op: request.operationId,
            route: request.route,
            kind: apiError.kind,
            ...(apiError.kind === 'http' ? { status: apiError.status, requestId: apiError.requestId } : {}),
            ...(apiError.kind === 'contract'
              ? { reason: apiError.reason, status: apiError.status, instancePath: apiError.instancePath, keyword: apiError.keyword }
              : {}),
            ms: nowMs() - started,
          });
        }
        throw apiError;
      } finally {
        timeout.clear();
      }
    },
  };
}

export interface FetchTransportDeps extends TransportDeps {
  readonly fetchImpl?: typeof fetch;
}

/** Transporte real: `fetch` con credentials omit, no-store, no-referrer y redirect manual. */
export function createFetchTransport(deps: FetchTransportDeps): Transport {
  const fetchImpl = deps.fetchImpl ?? ((input: RequestInfo | URL, init?: RequestInit) => globalThis.fetch(input, init));
  return createTransport({ ...deps, dispatch: (request) => fetchImpl(request) });
}

// --- Transporte activo (main.tsx lo instala según el perfil) ---

let active: Transport | null = null;

export function setTransport(transport: Transport | null): void {
  active = transport;
}

export function getTransport(): Transport {
  if (active === null) throw new ApiError({ kind: 'config' });
  return active;
}
