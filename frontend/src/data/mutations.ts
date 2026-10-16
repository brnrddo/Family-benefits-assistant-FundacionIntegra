// Mutations C3: conversación (FE-006/FE-007, design.md §9.4/§12.4), preevaluación (§9.6) y asistente
// (§9.8). Sin señal del llamador: salir de la vista no aborta el POST (NIT 8). Sin red en Demo, la
// conversación va a la cola local; en Escala no se persiste nada.
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { askCatalogAssistant, createConversacion, createPreevaluacion } from '../api/client';
import { isApiError } from '../api/errors';
import { addFamiliaAntecedentes } from '../api/proposals/addInfo';
import type { AddFamilyInfoRequestV1 } from '../api/proposals/types';
import type { ConversationRequest, PreevaluationRequest } from '../api/types';
import { getSession } from '../auth/session';
import { runtimeConfig } from '../config/profile';
import { classifyConversationError, discardEntry, enqueue, queueStatusFor } from '../offline/conversationQueue';
import { recordDoneAction } from '../offline/doneActions';
import { invalidateAfterConversation } from './queryClient';
import { primeFamilia, queryKeys } from './queries';

export type ConversationOutcome =
  | 'confirmed'
  | 'queued'
  | 'queue_disabled'
  | 'paused_auth'
  | 'login_required'
  | 'conflict'
  | 'unavailable'
  | 'rejected';

export interface SubmitConversationInput {
  readonly familyId: string;
  readonly gardenId: string;
  readonly body: ConversationRequest;
  /** Misma clave en cada reintento del MISMO cuerpo; cuerpo nuevo → clave nueva. */
  readonly idempotencyKey: string;
}

export async function submitConversation(input: SubmitConversationInput): Promise<ConversationOutcome> {
  const queueEnabled = runtimeConfig().capabilities.queue;
  const session = getSession();
  try {
    await createConversacion({ familyId: input.familyId, body: input.body, idempotencyKey: input.idempotencyKey });
    return 'confirmed';
  } catch (error) {
    const failure = classifyConversationError(error, session.authMode);
    const httpStatus = isApiError(error) && error.kind === 'http' ? error.status : null;
    const persist = async (): Promise<boolean> =>
      queueEnabled && (await enqueue({ ...input, status: queueStatusFor(failure), lastHttpStatus: httpStatus })).persisted;

    switch (failure) {
      case 'retry_later': {
        if (await persist()) return 'queued';
        return isApiError(error) && error.kind === 'auth_required' ? 'login_required' : 'queue_disabled';
      }
      case 'paused_auth':
        session.toAnonymous('expired');
        return (await persist()) ? 'paused_auth' : 'login_required';
      case 'manual':
        await persist();
        return 'unavailable';
      case 'cancelled':
        return 'unavailable';
      case 'conflict':
        return 'conflict';
      default:
        return 'rejected';
    }
  }
}

export function useSubmitConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: submitConversation,
    onSuccess: async (outcome, input) => {
      // DEC-091: memoria local de la acción del día (confirmada o ya guardada en la cola del equipo).
      if (outcome === 'confirmed' || outcome === 'queued' || outcome === 'paused_auth') {
        await recordDoneAction(input.familyId, input.body.benefit_ids[0] ?? null);
      }
      if (outcome === 'confirmed') {
        // Un reintento manual confirmado deja de estar pendiente en este equipo (misma clave).
        await discardEntry(input.idempotencyKey).catch(() => undefined);
        await invalidateAfterConversation(queryClient);
      }
      if (outcome === 'conflict') await queryClient.invalidateQueries({ queryKey: queryKeys.familia(input.familyId) });
    },
  });
}

export interface SubmitPreevaluationInput {
  readonly body: PreevaluationRequest;
  /** Misma clave al reintentar el MISMO cuerpo (§9.6); cuerpo nuevo → clave nueva. */
  readonly idempotencyKey: string;
}

/** Ficha nueva (§9.6): resultado PRELIMINAR de C3. Un 200 válido invalida el KPI (NIT 10). */
export function useSubmitPreevaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitPreevaluationInput) => createPreevaluacion(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kpi'] }),
  });
}

export interface SubmitAddInfoInput {
  readonly familyId: string;
  readonly body: AddFamilyInfoRequestV1;
  /** Misma clave al reintentar el MISMO cuerpo; cuerpo nuevo → clave nueva. */
  readonly idempotencyKey: string;
}

/**
 * "Agregar información" (DEC-039, operación PROPUESTA fuera de C3): solo en línea, sin cola. La API
 * re-evalúa y devuelve la ficha (PRELIMINAR); se usa tal cual y se refrescan lista y oportunidades.
 */
export function useSubmitAddInfo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitAddInfoInput) => addFamiliaAntecedentes(input),
    onSuccess: async (ok, input) => {
      primeFamilia(queryClient, input.familyId, ok);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['oportunidades', input.familyId] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.contexto(input.familyId) }),
        queryClient.invalidateQueries({ queryKey: ['familias'] }),
        // Campos ya declarados (GET /antecedentes, DEC-093): no se vuelven a preguntar.
        queryClient.invalidateQueries({ queryKey: ['antecedentes', input.familyId] }),
      ]);
    },
  });
}

/** Asistente de catálogo (§9.8): pregunta y respuesta solo en memoria (gcTime 0, nada persiste). */
export function useAskAssistant() {
  return useMutation({
    mutationFn: (question: string) => askCatalogAssistant({ body: { question } }),
    gcTime: 0,
  });
}
