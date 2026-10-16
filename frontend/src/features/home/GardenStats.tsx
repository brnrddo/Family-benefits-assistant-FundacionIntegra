// Estadísticas del jardín en Inicio (plan de arreglos §7): cifras de C3 tal cual (sin recalcular).
// Familias y % informadas vienen del resumen del jardín (`/jardines`); "Lo que más se repite" son los
// `top_gaps` de `GET /kpi` del jardín. Si el KPI falla o viene suprimido, solo se omite ese bloque.
import { useKpi } from '../../data/queries';
import type { JardinSummary } from '../../api/types';
import { formatClp, formatInteger, formatPercent } from '../../domain/format';
import { benefitLabel, t } from '../../i18n/copy';
import { Card } from '../../ui/Card';
import { DEMO_COPY, familiesCount } from '../demo-session/demoCopy';

function Figure({ value, label }: { readonly value: string; readonly label: string }) {
  return (
    <div className="flex flex-col items-center rounded-xl bg-canvas px-2 py-3 text-center">
      <span className="text-2xl font-bold text-primary">{value}</span>
      <span className="text-[0.85rem] font-semibold text-ink-muted">{label}</span>
    </div>
  );
}

export function GardenStats({ garden }: { readonly garden: JardinSummary }) {
  const kpi = useKpi({ nivel: 'jardin', id: garden.garden_id });
  const data = kpi.data?.body.data;
  const gaps = data !== undefined && !data.suppressed ? [...data.top_gaps].sort((a, b) => b.family_count - a.family_count).slice(0, 3) : [];
  const opportunities = gaps.reduce((sum, gap) => sum + gap.family_count, 0);
  return (
    <Card className="space-y-4">
      <h2>{DEMO_COPY.statsTitle}</h2>
      <div className="grid grid-cols-3 gap-2">
        <Figure value={formatInteger(garden.families_total)} label={DEMO_COPY.statsFamilies} />
        <Figure
          value={garden.informed_percentage === null ? '—' : formatPercent(garden.informed_percentage)}
          label={DEMO_COPY.statsInformed}
        />
        <Figure value={gaps.length > 0 ? formatInteger(opportunities) : '—'} label={DEMO_COPY.statsOpportunities} />
      </div>
      {garden.informed_percentage !== null && (
        <progress className="progress" max={100} value={garden.informed_percentage} aria-label={t('home.progress_label')} />
      )}
      <p>{t('home.progress', { informed: formatInteger(garden.families_informed), total: formatInteger(garden.families_total) })}</p>
      {gaps.length > 0 && (
        <section aria-labelledby="home-top-gaps" className="space-y-2">
          <h3 id="home-top-gaps">{DEMO_COPY.statsTopTitle}</h3>
          <ol className="space-y-2">
            {gaps.map((gap) => (
              <li key={gap.benefit_id} className="flex items-baseline justify-between gap-3 rounded-xl border border-border p-3">
                <span className="font-semibold">{benefitLabel(gap.benefit_id)}</span>
                <span className="shrink-0 text-right text-ink-muted">
                  {familiesCount(formatInteger(gap.family_count))}
                  {gap.potential_annual_amount !== null && (
                    <span className="block text-[0.85rem]">{formatClp(gap.potential_annual_amount)}</span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </Card>
  );
}
