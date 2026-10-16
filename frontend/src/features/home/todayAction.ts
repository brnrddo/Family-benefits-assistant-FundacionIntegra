// Acción del día (DEC-091): UNA familia y UN apoyo, tal como los ordena el motor. Solo presentación:
// familias sin conversar (C3 `conversation_status`), sin acción hecha en este equipo ni en la cola
// local, con al menos un `top_benefit_ids`; orden por `priority_score` de C3 (desempate por
// `family_id`) y el primer apoyo de `top_benefit_ids`. No recalcula elegibilidad ni ranking.
import { generatePath } from 'react-router';
import type { FamilySummary } from '../../api/types';
import { shortFamilyId } from '../../domain/familyName';
import { benefitLabel } from '../../i18n/copy';
import { now } from '../../lib/now';
import { useQueueSummary } from '../../offline/conversationQueue';
import { useDoneActions, type DoneAction } from '../../offline/doneActions';
import { useLocalNames } from '../../offline/localNames';
import { chatMemory, whenLabel } from '../demo-session/demoCopy';

export interface DayAction {
  readonly family: FamilySummary;
  readonly benefitId: string;
}

export const familyPath = (familyId: string): string => generatePath('/familias/:familyId', { familyId });

export function dayActions(
  families: readonly FamilySummary[],
  doneIds: ReadonlySet<string>,
  pendingIds: ReadonlySet<string>,
): DayAction[] {
  return families
    .filter(
      (f) =>
        f.conversation_status !== 'CONVERSADA' && !doneIds.has(f.family_id) && !pendingIds.has(f.family_id) && f.top_benefit_ids.length > 0,
    )
    .sort((a, b) => b.priority_score - a.priority_score || (a.family_id < b.family_id ? -1 : a.family_id > b.family_id ? 1 : 0))
    .map((family) => ({ family, benefitId: family.top_benefit_ids[0] ?? '' }));
}

/** "la familia de Antonella" (primer nombre de trato local) o "la familia 00364" sin nombre. */
export function familyCall(familyId: string, names: ReadonlyMap<string, string>): string {
  const first = names.get(familyId)?.split(' ')[0];
  return first !== undefined && first !== '' ? `la familia de ${first}` : `la familia ${shortFamilyId(familyId)}`;
}

const localDay = (date: Date): number => Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());

/** Días calendario locales entre la acción y hoy (0 = hoy). */
export function daysAgo(doneAt: string, today: Date = now()): number {
  return Math.max(0, Math.round((localDay(today) - localDay(new Date(doneAt))) / 86_400_000));
}

export interface DayPlan {
  readonly actions: readonly DayAction[];
  /** Lo último que hizo la tía en este equipo (o null). */
  readonly last: DoneAction | null;
  readonly names: ReadonlyMap<string, string>;
}

export function useDayPlan(families: readonly FamilySummary[]): DayPlan {
  const done = useDoneActions();
  const queue = useQueueSummary();
  const names = useLocalNames();
  const doneIds = new Set(done.map((action) => action.family_id));
  return { actions: dayActions(families, doneIds, queue.pendingFamilyIds), last: done[0] ?? null, names };
}

/** Saludo del chat que recuerda lo hecho y sugiere lo de hoy (texto local, nunca se envía). */
export function memoryGreeting(plan: DayPlan): string | null {
  const next = plan.actions[0];
  return chatMemory(
    plan.last === null
      ? null
      : {
          who: familyCall(plan.last.family_id, plan.names),
          benefit: plan.last.benefit_id === null ? null : benefitLabel(plan.last.benefit_id),
          when: whenLabel(daysAgo(plan.last.done_at)),
        },
    next === undefined ? null : { who: familyCall(next.family.family_id, plan.names), benefit: benefitLabel(next.benefitId) },
  );
}
