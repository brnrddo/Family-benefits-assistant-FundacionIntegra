// Hooks de lectura C3 (design.md §6.4, §9). Las vistas solo usan estos hooks: muestran lo que
// entrega C3 sin recalcular elegibilidad, acceso, U/B/V, posición ni porcentajes (FE-003).
// Lecturas GET: red → snapshot → caché Demo; con red caída/timeout/sin sesión offline, caché Demo.
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import * as client from '../api/client';
import { isApiError } from '../api/errors';
import {
  validateFamiliaDetailEnvelope,
  validateFamiliaListEnvelope,
  validateJardinListEnvelope,
  validateOpportunityListEnvelope,
  type ValidateFn,
} from '../api/generated/validators.gen.js';
import { snapshotIdOf, snapshotStore } from '../api/snapshot';
import type { C3Ok, FamiliaListEnvelope, OpportunityOrder } from '../api/types';
import { readCache, writeCache, type CacheKey } from '../offline/demoCache';
import { isOnline } from '../offline/network';
import type { ReadResult } from './queryClient';

const GENERATION_GC_MS = 30 * 60_000;

export const queryKeys = {
  jardines: () => ['jardines'] as const,
  familias: (gardenId: string) => ['familias', gardenId] as const,
  familia: (familyId: string) => ['familia', familyId] as const,
  contexto: (familyId: string) => ['contexto', familyId] as const,
  oportunidades: (familyId: string, orden: OpportunityOrder) => ['oportunidades', familyId, orden] as const,
  guion: (familyId: string, benefitIds: readonly string[]) => ['guion', familyId, ...benefitIds] as const,
  mensaje: (familyId: string, benefitIds: readonly string[]) => ['mensaje', familyId, ...benefitIds] as const,
  kpi: (params: client.KpiParams) => ['kpi', params.nivel, params.id ?? null, params.desde ?? null, params.hasta ?? null] as const,
};

interface CachePlan<T> {
  readonly key: CacheKey;
  readonly validate: ValidateFn<T>;
}

function shouldUseCache(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return error.kind === 'network' || error.kind === 'timeout' || (error.kind === 'auth_required' && !isOnline());
}

/** Registra el snapshot y, si corresponde, escribe la caché DESPUÉS de persistir el snapshot (§6.2). */
function recordNetworkRead<T>(ok: C3Ok<T>, cache: CachePlan<T> | null): void {
  const snapshotId = snapshotIdOf(ok.body);
  void snapshotStore
    .observe(snapshotId)
    .then(() => (cache === null ? undefined : writeCache(cache.key, ok.body, snapshotId)))
    .catch(() => undefined);
}

export async function readThrough<T>(fetcher: () => Promise<C3Ok<T>>, cache: CachePlan<T> | null): Promise<ReadResult<T>> {
  try {
    const ok = await fetcher();
    recordNetworkRead(ok, cache);
    return { source: 'network', body: ok.body, requestId: ok.requestId, receivedAt: ok.receivedAt };
  } catch (error) {
    if (cache !== null && shouldUseCache(error)) {
      const cached = await readCache(cache.key, cache.validate);
      if (cached !== null) return { source: 'cache', body: cached.body, storedAt: cached.storedAt };
    }
    throw error;
  }
}

/** Jardines asignados (una página de hasta 100: cubre los 50 jardines Demo). */
export function useJardines() {
  return useQuery({
    queryKey: queryKeys.jardines(),
    queryFn: ({ signal }) =>
      readThrough(() => client.listJardines({}, { signal }), { key: 'jardines', validate: validateJardinListEnvelope }),
  });
}

/** Familias del jardín en el orden de C3, con cursor opaco ("Cargar más"). Solo la 1.ª página se cachea. */
export function useFamilias(gardenId: string | undefined) {
  return useInfiniteQuery({
    queryKey: queryKeys.familias(gardenId ?? ''),
    enabled: gardenId !== undefined,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }): Promise<ReadResult<FamiliaListEnvelope>> =>
      readThrough(
        () => client.listFamiliasByJardin({ gardenId: gardenId ?? '', ...(pageParam !== null ? { cursor: pageParam } : {}) }, { signal }),
        pageParam === null ? { key: `familias:${gardenId ?? ''}`, validate: validateFamiliaListEnvelope } : null,
      ),
    getNextPageParam: (last) => last.body.next_cursor ?? undefined,
  });
}

export function useFamilia(familyId: string) {
  return useQuery({
    queryKey: queryKeys.familia(familyId),
    queryFn: ({ signal }) =>
      readThrough(() => client.getFamilia({ familyId }, { signal }), {
        key: `familia:${familyId}`,
        validate: validateFamiliaDetailEnvelope,
      }),
  });
}

/** Contexto familiar: solo memoria, nunca caché persistente (SUP-032, minimización). */
export function useContexto(familyId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.contexto(familyId),
    enabled,
    queryFn: ({ signal }) => readThrough(() => client.getContextoFamilia({ familyId }, { signal }), null),
  });
}

export function useOportunidades(familyId: string, orden: OpportunityOrder, enabled = true) {
  return useQuery({
    queryKey: queryKeys.oportunidades(familyId, orden),
    enabled,
    queryFn: ({ signal }) =>
      readThrough(
        () => client.listOportunidades({ familyId, orden }, { signal }),
        orden === 'prioridad' ? { key: `oportunidades:${familyId}:prioridad`, validate: validateOpportunityListEnvelope } : null,
      ),
  });
}

/** Guion (POST de generación) como query en memoria: no se persiste ni se reintenta solo. */
export function useGuion(familyId: string, benefitIds: readonly string[]) {
  return useQuery({
    queryKey: queryKeys.guion(familyId, benefitIds),
    enabled: benefitIds.length > 0,
    staleTime: Infinity,
    gcTime: GENERATION_GC_MS,
    retry: false,
    queryFn: async () => {
      const ok = await client.createGuion({ familyId, body: { benefit_ids: [...benefitIds] } });
      recordNetworkRead(ok, null);
      return ok;
    },
  });
}

/**
 * KPI agregado de C3 (§9.7): valores tal cual, sin recalcular; no se cachea en IndexedDB.
 * `params = null` deja la query inactiva (sin jardín o con rango inválido no se consulta).
 */
export function useKpi(params: client.KpiParams | null) {
  return useQuery({
    queryKey: params === null ? ['kpi', 'idle'] : queryKeys.kpi(params),
    enabled: params !== null,
    queryFn: ({ signal }) => readThrough(() => client.getKpi(params ?? { nivel: 'nacional' }, { signal }), null),
  });
}

/** Mensaje WhatsApp (solo vista previa) + tarjeta CARD_V1, en memoria. */
export function useMensaje(familyId: string, benefitIds: readonly string[]) {
  return useQuery({
    queryKey: queryKeys.mensaje(familyId, benefitIds),
    enabled: benefitIds.length > 0,
    staleTime: Infinity,
    gcTime: GENERATION_GC_MS,
    retry: false,
    queryFn: async () => {
      const ok = await client.createMensaje({ familyId, body: { benefit_ids: [...benefitIds] } });
      recordNetworkRead(ok, null);
      return ok;
    },
  });
}
