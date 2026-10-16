// Tarjeta "Hoy" de Inicio (DEC-091): UNA frase de acción con la familia que sigue según el motor, un
// acceso directo a su ficha y "Ya le informé". Encima, si sus oportunidades ya cargaron, un resumen
// determinista ("tiene 3 apoyos posibles y solo le faltan 2 datos"); si cargan, fallan o no hay
// apoyos, se ve solo la frase de acción. Al registrar, la memoria local pasa a la siguiente familia y
// muestra "Hoy habló con… ✓". Las 2 siguientes quedan plegadas.
import type { FamilySummary } from '../../api/types';
import { useFamilia, useOportunidades } from '../../data/queries';
import { benefitStatus, firstName, householdLine } from '../assistant/familyHint';
import { benefitLabel } from '../../i18n/copy';
import { ButtonLink } from '../../ui/Button';
import { Expandable } from '../../ui/Expandable';
import { QuickInformButton } from '../conversation/QuickInform';
import { DEMO_COPY, doneLine, todayLead, todayMore, todaySummaryLine, whenLabel } from '../demo-session/demoCopy';
import { daysAgo, familyCall, familyPath, todaySummary, useDayPlan } from './todayAction';

const MORE = 2;

export function TodayCard({
  families,
  gardenId,
  snapshotId,
}: {
  readonly families: readonly FamilySummary[];
  readonly gardenId: string;
  readonly snapshotId: string | undefined;
}) {
  const plan = useDayPlan(families);
  const [first, ...rest] = plan.actions;
  const more = rest.slice(0, MORE);
  // Misma query que la ficha (comparte caché). Se llama siempre (reglas de hooks), solo pide con familia.
  const oportunidades = useOportunidades(first?.family.family_id ?? '', 'prioridad', first !== undefined);
  const ficha = useFamilia(first?.family.family_id ?? '', first !== undefined);
  const summary = first !== undefined && oportunidades.data !== undefined ? todaySummary(oportunidades.data.body.items) : null;
  // Pista (solo pantalla): hogar, tramo y el porqué del apoyo del día. Sin ficha cargada, no se muestra.
  const detail = first !== undefined ? ficha.data?.body.data : undefined;
  const todayOpportunity = oportunidades.data?.body.items.find((o) => o.benefit_id === first?.benefitId);
  // El apoyo ya va nombrado en la frase de acción: la pista solo agrega el porqué.
  const hint =
    first === undefined || detail === undefined
      ? null
      : [
          householdLine(detail.composition, detail.rsh_band, firstName(first.family.family_id, plan.names)),
          ...(todayOpportunity !== undefined ? [`Por qué: ${benefitStatus(todayOpportunity)}.`] : []),
        ].join(' ');
  return (
    <section aria-labelledby="home-today" data-today-action className="space-y-3 rounded-card border-2 border-primary bg-surface p-5 shadow-sm">
      <h2 id="home-today">{DEMO_COPY.todayTitle}</h2>
      {first === undefined ? (
        <p className="text-lg">{DEMO_COPY.todayAllDone}</p>
      ) : (
        <>
          <p className="text-lg" data-today-text>
            {summary !== null && (
              <span data-today-summary className="mb-1 block font-semibold">
                {todaySummaryLine(familyCall(first.family.family_id, plan.names), summary.possible, summary.missing)}
              </span>
            )}
            {todayLead(familyCall(first.family.family_id, plan.names))}{' '}
            <strong>{benefitLabel(first.benefitId)}</strong>
          </p>
          {hint !== null && (
            <p data-today-hint className="text-ink-muted">
              {hint}
            </p>
          )}
          <ButtonLink to={familyPath(first.family.family_id)} icon="child" className="w-full">
            {DEMO_COPY.todayOpenFamily}
          </ButtonLink>
          {snapshotId !== undefined && (
            <QuickInformButton
              key={first.family.family_id}
              familyId={first.family.family_id}
              gardenId={gardenId}
              benefitIds={first.family.top_benefit_ids}
              snapshotId={snapshotId}
              informed={false}
            />
          )}
          {more.length > 0 && (
            <Expandable openLabel={todayMore(more.length)} closeLabel={DEMO_COPY.todayHideMore}>
              <ul className="space-y-1">
                {more.map((action) => (
                  <li key={action.family.family_id}>
                    {todayLead(familyCall(action.family.family_id, plan.names))} {benefitLabel(action.benefitId)}
                  </li>
                ))}
              </ul>
            </Expandable>
          )}
        </>
      )}
      {plan.last !== null && (
        <p data-done-line className="font-semibold text-go-ink">
          {doneLine(familyCall(plan.last.family_id, plan.names), whenLabel(daysAgo(plan.last.done_at)))}
        </p>
      )}
    </section>
  );
}
