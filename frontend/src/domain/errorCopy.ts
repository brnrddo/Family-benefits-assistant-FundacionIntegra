// Error → clave de copy (design.md §6.4). Solo depende del tipo/status: el `message` del servidor
// nunca se muestra; lo único que se enseña del cuerpo es el request_id como código de ayuda.
import { isApiError, isUnexpectedStatus } from '../api/errors';
import type { PlainCopyKey } from '../i18n/copy';

const HTTP_KEYS: Readonly<Record<number, PlainCopyKey>> = {
  400: 'error.bad_request',
  401: 'error.unauthorized',
  403: 'error.forbidden',
  404: 'error.not_found',
  409: 'error.conflict',
  422: 'error.unprocessable',
  429: 'error.throttled',
};

export function errorCopyKey(error: unknown): PlainCopyKey {
  if (!isApiError(error)) return 'error.generic.body';
  switch (error.kind) {
    case 'network':
      return 'error.network';
    case 'timeout':
      return 'error.timeout';
    case 'auth_required':
      return 'error.unauthorized';
    case 'contract':
      return error.reason === 'invalid_param' ? 'error.not_found' : 'error.contract';
    case 'http':
      if (isUnexpectedStatus(error)) return 'error.contract';
      return HTTP_KEYS[error.status] ?? (error.status >= 500 ? 'error.unavailable' : 'error.contract');
    default:
      return 'error.generic.body';
  }
}

/** Reintentar tiene sentido en red, timeout, conflicto, 429 y 5xx. */
export function isRetryableError(error: unknown): boolean {
  if (!isApiError(error)) return true;
  if (error.kind === 'network' || error.kind === 'timeout' || error.kind === 'cancelled') return true;
  if (error.kind === 'http') return error.status === 409 || error.status === 429 || error.status >= 500;
  return false;
}

export function helpCodeOf(error: unknown): string | null {
  return isApiError(error) && error.kind === 'http' ? error.requestId : null;
}
