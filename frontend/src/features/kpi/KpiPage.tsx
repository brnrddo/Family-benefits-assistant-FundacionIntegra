// Avance / KPI (design.md §9.7, FE-001/FE-003/FE-005): agregados de C3 TAL CUAL. `suppressed: true`
// ⇒ no se muestra NINGUNA cifra (aunque vengan); `null` ⇒ "Sin dato", nunca 0. Las barras por jardín
// se eligen por igualdad de IDs de `listJardines`, sin sumar ni recalcular. Sin acción principal (V-01).
import { useId, useState } from 'react';
import { kpiMaxQueryDays } from 'virtual:brujula-content';
import type { KpiParams } from '../../api/client';
import type { JardinSummary, KpiLevel, KpiResult } from '../../api/types';
import { useKpi } from '../../data/queries';
import { formatClp, formatDate, formatInteger, formatPercent, formatRelative } from '../../domain/format';
import { KPI_LEVEL_KEY } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { nowMs } from '../../lib/now';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { DataFreshness } from '../../ui/DataStatus';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, Skeleton } from '../../ui/states';
import { useSelectedGarden } from '../system/useSelectedGarden';

const LEVELS: readonly KpiLevel[] = ['jardin', 'comuna', 'region', 'nacional'];
const DAY_MS = 86_400_000;

interface Range {
  readonly desde: string;
  readonly hasta: string;
}

type RangeError = 'kpi.range_invalid' | 'kpi.range_too_long' | null;

/** Validación previa de UX (el servidor sigue siendo la autoridad): desde ≤ hasta y tope de C4 si es VALID. */
function rangeError({ desde, hasta }: Range): RangeError {
  if (desde !== '' && hasta !== '' && desde > hasta) return 'kpi.range_invalid';
  if (desde !== '' && hasta !== '' && kpiMaxQueryDays !== null) {
    const days = Math.round((Date.parse(`${hasta}T00:00:00Z`) - Date.parse(`${desde}T00:00:00Z`)) / DAY_MS) + 1;
    if (days > kpiMaxQueryDays) return 'kpi.range_too_long';
  }
  return null;
}

function scopeId(level: KpiLevel, garden: JardinSummary): string | undefined {
  if (level === 'jardin') return garden.garden_id;
  if (level === 'comuna') return garden.commune_id;
  if (level === 'region') return garden.region_id;
  return undefined;
}

const percentOrNull = (value: number | null) => (value === null ? t('common.not_available') : formatPercent(value));

function Progress({ value, label }: { readonly value: number | null; readonly label: string }) {
  if (value === null) return <p>{t('common.not_available')}</p>;
  return (
    <>
      <progress className="progress" max={100} value={value} aria-label={label} />
      <p className="text-lg font-bold">{formatPercent(value)}</p>
    </>
  );
}

/** Jardines del alcance por igualdad de IDs (comuna/región/país). Nunca con `suppressed` ni con período. */
function GardenBars({ level, garden, gardens, labelledBy }: {
  readonly level: KpiLevel;
  readonly garden: JardinSummary;
  readonly gardens: readonly JardinSummary[];
  readonly labelledBy: string;
}) {
  if (level === 'jardin') return null;
  const rows = gardens.filter((g) =>
    level === 'comuna' ? g.commune_id === garden.commune_id : level === 'region' ? g.region_id === garden.region_id : true,
  );
  if (rows.length === 0) return null;
  return (
    <ul aria-labelledby={labelledBy} className="space-y-3 border-t border-border pt-3">
      {rows.map((row) => (
        <li key={row.garden_id} className="space-y-1">
          <p className="font-semibold">{t('home.garden_label', { garden_id: row.garden_id })}</p>
          {row.informed_percentage === null ? (
            <p>{t('common.not_available')}</p>
          ) : (
            <progress
              className="progress"
              max={100}
              value={row.informed_percentage}
              aria-label={t('home.garden_label', { garden_id: row.garden_id })}
            />
          )}
          <p className="text-ink-muted">
            {t('home.progress', { informed: formatInteger(row.families_informed), total: formatInteger(row.families_total) })}
          </p>
        </li>
      ))}
    </ul>
  );
}

function KpiFigures({ kpi, garden, gardens, filtered }: {
  readonly kpi: KpiResult;
  readonly garden: JardinSummary;
  readonly gardens: readonly JardinSummary[];
  readonly filtered: boolean;
}) {
  const informedId = useId();
  return (
    <>
      <Card className="space-y-3">
        <h2 id={informedId}>{t('kpi.informed')}</h2>
        <Progress value={kpi.informed_percentage} label={t('kpi.informed')} />
        <p>{t('kpi.ratio', { informed: formatInteger(kpi.informed_families), total: formatInteger(kpi.total_families) })}</p>
        {!filtered && <GardenBars level={kpi.level} garden={garden} gardens={gardens} labelledBy={informedId} />}
      </Card>
      <Card className="space-y-3">
        <h2>{t('kpi.informed_new')}</h2>
        <Progress value={kpi.informed_new_percentage} label={t('kpi.informed_new')} />
        <p>
          {t('kpi.ratio', { informed: formatInteger(kpi.informed_new_families), total: formatInteger(kpi.total_new_families) })}
        </p>
      </Card>
      <Card className="space-y-2">
        <h2>{t('kpi.coverage')}</h2>
        <p className="text-lg font-bold">{percentOrNull(kpi.opportunity_coverage_percentage)}</p>
      </Card>
      {kpi.top_gaps.length > 0 && (
        <section aria-labelledby="kpi-gaps" className="space-y-2">
          <h2 id="kpi-gaps">{t('kpi.gaps_title')}</h2>
          <ol className="space-y-2">
            {kpi.top_gaps.map((gap) => (
              <li key={gap.benefit_id} className="rounded-xl border border-border bg-surface p-3">
                <p className="c3-text font-semibold">{benefitName(gap.benefit_id)}</p>
                <p>{t('kpi.gap_families', { count: formatInteger(gap.family_count) })}</p>
                <p className="text-ink-muted">
                  {gap.potential_annual_amount === null
                    ? t('common.not_available')
                    : t('kpi.gap_amount', { amount: formatClp(gap.potential_annual_amount) })}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}

function KpiView({ garden, gardens, onSelectGarden }: {
  readonly garden: JardinSummary;
  readonly gardens: readonly JardinSummary[];
  readonly onSelectGarden: (gardenId: string) => void;
}) {
  const [level, setLevel] = useState<KpiLevel>('jardin');
  const [draft, setDraft] = useState<Range>({ desde: '', hasta: '' });
  const [applied, setApplied] = useState<Range>({ desde: '', hasta: '' });
  const [error, setError] = useState<RangeError>(null);
  const fromId = useId();
  const toId = useId();

  const id = scopeId(level, garden);
  const params: KpiParams = {
    nivel: level,
    ...(id !== undefined ? { id } : {}),
    ...(applied.desde !== '' ? { desde: applied.desde } : {}),
    ...(applied.hasta !== '' ? { hasta: applied.hasta } : {}),
  };
  const kpi = useKpi(params);

  const apply = () => {
    const problem = rangeError(draft);
    setError(problem);
    if (problem === null) setApplied(draft); // con error en línea no se consulta
  };

  let figures;
  if (kpi.isPending) figures = <Skeleton rows={3} rowClass="h-28" />;
  else if (kpi.isError && kpi.data === undefined) figures = <ErrorState error={kpi.error} onRetry={() => void kpi.refetch()} />;
  else if (kpi.data !== undefined) {
    const data = kpi.data.body.data;
    figures = (
      <>
        <DataFreshness result={kpi.data} />
        <p className="text-ink-muted">
          {t('kpi.period', { start: formatDate(data.period_start), end: formatDate(data.period_end) })} ·{' '}
          {t('kpi.calculated_at', { when: formatRelative(data.calculated_at, nowMs()) })}
        </p>
        {data.suppressed ? (
          <EmptyState icon="info" message={t('kpi.suppressed')} />
        ) : (
          <KpiFigures kpi={data} garden={garden} gardens={gardens} filtered={applied.desde !== '' || applied.hasta !== ''} />
        )}
      </>
    );
  }

  return (
    <>
      {gardens.length > 1 && (
        <ChoiceChips
          legend={t('home.select_garden')}
          options={gardens.map((g) => ({ value: g.garden_id, label: t('home.garden_label', { garden_id: g.garden_id }) }))}
          value={garden.garden_id}
          onChange={onSelectGarden}
        />
      )}
      <ChoiceChips
        legend={t('kpi.level_label')}
        options={LEVELS.map((value) => ({ value, label: t(KPI_LEVEL_KEY[value]) }))}
        value={level}
        onChange={(value) => setLevel(value as KpiLevel)}
      />
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label htmlFor={fromId} className="block font-semibold">
            {t('kpi.from_label')}
          </label>
          <input
            id={fromId}
            type="date"
            value={draft.desde}
            onChange={(event) => setDraft({ ...draft, desde: event.target.value })}
            className="min-h-12 w-full rounded-xl border-2 border-border-strong bg-surface px-2"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor={toId} className="block font-semibold">
            {t('kpi.to_label')}
          </label>
          <input
            id={toId}
            type="date"
            value={draft.hasta}
            onChange={(event) => setDraft({ ...draft, hasta: event.target.value })}
            aria-invalid={error !== null || undefined}
            aria-describedby={error !== null ? `${toId}-error` : undefined}
            className="min-h-12 w-full rounded-xl border-2 border-border-strong bg-surface px-2"
          />
        </div>
      </div>
      {error !== null && (
        <p id={`${toId}-error`} role="alert" className="font-semibold text-danger-ink">
          {error === 'kpi.range_invalid'
            ? t('kpi.range_invalid')
            : t('kpi.range_too_long', { max_days: formatInteger(kpiMaxQueryDays ?? 0) })}
        </p>
      )}
      <Button variant="secondary" className="w-full" onClick={apply}>
        {t('kpi.apply')}
      </Button>
      {figures}
    </>
  );
}

export default function KpiPage() {
  const { jardines, gardens, garden, select } = useSelectedGarden();
  let body;
  if (jardines.isPending) body = <Skeleton rows={3} />;
  else if (jardines.isError && jardines.data === undefined) body = <ErrorState error={jardines.error} onRetry={() => void jardines.refetch()} />;
  else if (garden === undefined) body = <EmptyState message={t('empty.kpi')} />;
  else body = <KpiView key={garden.garden_id} garden={garden} gardens={gardens} onSelectGarden={select} />;
  return (
    <div className="space-y-5">
      <PageTitle>{t('kpi.title')}</PageTitle>
      {body}
    </div>
  );
}
