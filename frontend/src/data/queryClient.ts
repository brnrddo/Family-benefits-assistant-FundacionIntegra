// QueryClient de la app (design.md §6.4, §12.3): reintentos automáticos solo en GET con 429/5xx,
// datos de caché Demo stale al instante, sin refetch al enfocar y networkMode 'always' para que la
// queryFn corra offline y decida el fallback a caché.
import { QueryCache, QueryClient } from '@tanstack/react-query';
import { isApiError } from '../api/errors';
import { getSession } from '../auth/session';

/** Resultado de una lectura: red o caché Demo (solo local/demo sintético). */
export type ReadResult<T> =
  | { readonly source: 'network'; readonly body: T; readonly requestId: string | null; readonly receivedAt: string }
  | { readonly source: 'cache'; readonly body: T; readonly storedAt: string };

/** true si la query (simple o infinite: su primera página) viene de la caché Demo. */
export function fromCache(data: unknown): boolean {
  if (data === null || typeof data !== 'object') return false;
  if ('source' in data) return (data as { source: unknown }).source === 'cache';
  const pages = (data as { pages?: unknown }).pages;
  return Array.isArray(pages) && pages.some((page) => fromCache(page));
}

const STALE_MS = 60_000;
const GC_MS = 30 * 60_000;

export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError(error) {
        // 401 legible: la sesión Cognito pasa a anónima (en `none` es no-op y se ve el error).
        if (isApiError(error) && error.kind === 'http' && error.status === 401) {
          try {
            getSession().toAnonymous('expired');
          } catch {
            // sin sesión instalada (pruebas)
          }
        }
      },
    }),
    defaultOptions: {
      queries: {
        retry: (failureCount, error) =>
          isApiError(error) && error.kind === 'http' && (error.status === 429 || error.status >= 500) && failureCount < 2,
        retryDelay: (attempt) => [1000, 3000][attempt] ?? 3000,
        staleTime: (query) => (fromCache(query.state.data) ? 0 : STALE_MS),
        gcTime: GC_MS,
        refetchOnWindowFocus: false,
        networkMode: 'always',
      },
      mutations: { retry: false, networkMode: 'always' },
    },
  });
}

/** Al volver la red: las queries servidas desde caché se piden de nuevo al servidor. */
export function invalidateCachedQueries(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ predicate: (query) => fromCache(query.state.data) });
}

/** Tras una conversación confirmada (201): la barra y el KPI suben solo con datos del servidor. */
export async function invalidateAfterConversation(queryClient: QueryClient): Promise<void> {
  await Promise.all(
    [['familias'], ['jardines'], ['familia'], ['kpi']].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
  );
}
