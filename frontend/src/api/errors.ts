// ApiError discriminado (design.md §6.3). El `message` del servidor NUNCA se guarda ni se
// muestra: la UI usa claves error.* según tipo/status y solo enseña `requestId` como código de ayuda.
import type { OperationId } from './types';

export type ContractReason = 'invalid_param' | 'content_type' | 'too_large' | 'encoding' | 'schema' | 'unexpected_status';

export type ApiErrorDetail =
  | { readonly kind: 'network' }
  | { readonly kind: 'timeout' }
  | { readonly kind: 'cancelled'; readonly cause: 'session' | 'caller' }
  | { readonly kind: 'auth_required' }
  | {
      readonly kind: 'http';
      readonly status: number;
      readonly code: string;
      readonly requestId: string | null;
      readonly retryable: boolean;
    }
  | {
      readonly kind: 'contract';
      readonly operationId: OperationId;
      readonly reason: ContractReason;
      readonly status?: number;
      readonly instancePath?: string;
      readonly keyword?: string;
    }
  | { readonly kind: 'config' };

export type ApiErrorKind = ApiErrorDetail['kind'];

class ApiErrorImpl extends Error {
  constructor(detail: ApiErrorDetail) {
    // Mensaje sin valores: solo el tipo (nunca el message del servidor ni datos de entrada).
    super(`api_error:${detail.kind}`);
    this.name = 'ApiError';
    Object.assign(this, detail);
  }
}

/** Instancia de Error con los campos del detalle (permite `e.kind === 'http' && e.status`). */
export type ApiError = ApiErrorImpl & ApiErrorDetail;

export const ApiError = ApiErrorImpl as unknown as {
  new (detail: ApiErrorDetail): ApiError;
  readonly prototype: ApiError;
};

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiErrorImpl;
}

export const RETRYABLE_STATUSES: ReadonlySet<number> = new Set([429, 500, 502, 503, 504]);

/** Statuses con fila propia en §6.4; el resto (1xx, 3xx, 405, 408, 410, 413, 415…) es "status inesperado". */
const STATUSES_WITH_ROW: ReadonlySet<number> = new Set([400, 401, 403, 404, 409, 422, 429]);

/**
 * Fila "status inesperado" de §6.4: `contract('unexpected_status')` (2xx distinto del esperado,
 * opaqueredirect, mock sin handler) o un `http` no-2xx sin fila propia y < 500.
 */
export function isUnexpectedStatus(error: ApiError): boolean {
  if (error.kind === 'contract') return error.reason === 'unexpected_status';
  if (error.kind === 'http') return error.status < 500 && !STATUSES_WITH_ROW.has(error.status);
  return false;
}

/** Fila "respuesta inválida" de §6.4 (con el status esperado). */
export function isInvalidResponse(error: ApiError): boolean {
  return (
    error.kind === 'contract' &&
    (error.reason === 'content_type' || error.reason === 'too_large' || error.reason === 'encoding' || error.reason === 'schema')
  );
}

export function contractError(
  operationId: OperationId,
  reason: ContractReason,
  extra: { status?: number; instancePath?: string; keyword?: string } = {},
): ApiError {
  return new ApiError({ kind: 'contract', operationId, reason, ...extra });
}
