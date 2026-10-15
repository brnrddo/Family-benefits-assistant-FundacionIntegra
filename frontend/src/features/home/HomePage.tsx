// Inicio / Mi jardín (design.md §9.1, FE-001/FE-003, DEC-037): avance del jardín y TODAS las
// familias en orden NEUTRO (alfabético por nombre de trato local; sin nombre, por family_id). Ya no
// se ordena ni destaca por prioridad familiar: cada tarjeta muestra sus acciones prioritarias
// (top_benefit_ids de C3), el semáforo, el estado de conversación y el total de oportunidades, tal
// como vienen de C3. Ordenar alfabéticamente no es recalcular ranking (no usa priority_score).
import { useEffect } from 'react';
import { generatePath, Link } from 'react-router';
import type { FamilySummary, JardinSummary } from '../../api/types';
import { useFamilias } from '../../data/queries';
import { familyDisplayName } from '../../domain/familyName';
import { sortFamiliesNeutral } from '../../domain/familyOrder';
import { formatInteger, formatPercent } from '../../domain/format';
import { CONVERSATION_STATUS_KEY, TRAFFIC_LIGHT_PRESENTATION, ZONE_KEY } from '../../domain/presentation';
import { benefitLabel, t } from '../../i18n/copy';
import { useQueueSummary } from '../../offline/conversationQueue';
import { useLocalNames } from '../../offline/localNames';
import { Card, CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { DataFreshness } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, Skeleton } from '../../ui/states';
import { QueuePanel } from '../conversation/QueuePanel';
import { useSelectedGarden } from '../system/useSelectedGarden';

const familyPath = (familyId: string) => generatePath('/familias/:familyId', { familyId });
/** Tope de páginas por jardín (E-3: ~10 familias por jardín, 25 por página). */
const MAX_PAGES = 20;

function ProgressCard({ garden }: { readonly garden: JardinSummary }) {
  return (
    <Card className="space-y-3">
      <h2>{t('home.progress_label')}</h2>
      <p className="text-ink-muted">
        {t('home.garden_label', { garden_id: garden.garden_id })} · {t(ZONE_KEY[garden.zone])}
      </p>
      {garden.informed_percentage === null ? (
        <p>{t('common.not_available')}</p>
      ) : (
        <>
          <progress className="progress" max={100} value={garden.informed_percentage} aria-label={t('home.progress_label')} />
          <p className="font-semibold">{t('home.progress_percent', { percent: formatPercent(garden.informed_percentage) })}</p>
        </>
      )}
      <p>
        {t('home.progress', { informed: formatInteger(garden.families_informed), total: formatInteger(garden.families_total) })}
      </p>
    </Card>
  );
}

function FamilyRow({ family, name, pendingLocal }: { readonly family: FamilySummary; readonly name: string; readonly pendingLocal: boolean }) {
  const light = TRAFFIC_LIGHT_PRESENTATION[family.traffic_light];
  return (
    <li>
      <Link to={familyPath(family.family_id)} data-family-row className={`${CARD_CLASS} flex items-center gap-3 hover:border-primary`}>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="font-bold">{name}</p>
          <div className="flex flex-wrap gap-2">
            <Chip icon={light.icon} tone={light.tone} label={t(light.labelKey)} />
            {pendingLocal && <Chip icon="clock" tone="ask" label={t('home.pending_local')} />}
          </div>
          {family.top_benefit_ids.length > 0 ? (
            <div>
              <p className="text-[0.9rem] font-semibold text-ink-muted">{t('home.priority_actions')}</p>
              <ul className="list-disc pl-6">
                {family.top_benefit_ids.map((benefitId) => (
                  <li key={benefitId}>{benefitLabel(benefitId)}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-ink-muted">{t('home.no_priority_actions')}</p>
          )}
          <p className="text-ink-muted">
            {t('home.opportunity_count', { count: formatInteger(family.opportunity_count) })} ·{' '}
            {t(CONVERSATION_STATUS_KEY[family.conversation_status])}
          </p>
        </div>
        <Icon name="chevron-left" className="size-6 rotate-180 text-ink-muted" />
      </Link>
    </li>
  );
}

function FamilyList({ garden }: { readonly garden: JardinSummary }) {
  const familias = useFamilias(garden.garden_id);
  const queue = useQueueSummary();
  const names = useLocalNames();
  const { hasNextPage, isFetchingNextPage, isFetchNextPageError, fetchNextPage } = familias;
  const pageCount = familias.data?.pages.length ?? 0;
  // DEC-037: se cargan TODAS las páginas del jardín antes de ordenar (orden neutro sobre la lista completa).
  const wantsMore = hasNextPage && !isFetchNextPageError && pageCount < MAX_PAGES;

  useEffect(() => {
    if (wantsMore && !isFetchingNextPage) void fetchNextPage();
  }, [wantsMore, isFetchingNextPage, fetchNextPage]);

  if (familias.isPending || (wantsMore && familias.data !== undefined)) return <Skeleton rows={5} />;
  if (familias.isError && familias.data === undefined) {
    return <ErrorState error={familias.error} onRetry={() => void familias.refetch()} />;
  }

  const items = sortFamiliesNeutral(familias.data?.pages.flatMap((page) => page.body.items) ?? [], names);

  return (
    <section aria-labelledby="home-list-title" className="space-y-3">
      <h2 id="home-list-title">{t('home.list_title')}</h2>
      <DataFreshness result={familias.data?.pages[0]} />
      {isFetchNextPageError && <ErrorState error={familias.error} onRetry={() => void fetchNextPage()} />}
      {items.length === 0 ? (
        <EmptyState message={t('empty.families')} />
      ) : (
        <ul className="space-y-3">
          {items.map((family) => (
            <FamilyRow
              key={family.family_id}
              family={family}
              name={familyDisplayName(family.family_id, names)}
              pendingLocal={queue.pendingFamilyIds.has(family.family_id)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default function HomePage() {
  const { jardines, gardens, garden, select } = useSelectedGarden();
  return (
    <div className="space-y-5">
      <PageTitle>{t('home.title')}</PageTitle>
      {jardines.isPending ? (
        <Skeleton rows={3} />
      ) : jardines.isError && jardines.data === undefined ? (
        <ErrorState error={jardines.error} onRetry={() => void jardines.refetch()} />
      ) : garden === undefined ? (
        <EmptyState message={t('empty.gardens')} />
      ) : (
        <>
          {gardens.length > 1 && (
            <ChoiceChips
              legend={t('home.select_garden')}
              options={gardens.map((g) => ({ value: g.garden_id, label: t('home.garden_label', { garden_id: g.garden_id }) }))}
              value={garden.garden_id}
              onChange={select}
            />
          )}
          <ProgressCard garden={garden} />
          <QueuePanel />
          <FamilyList key={garden.garden_id} garden={garden} />
        </>
      )}
    </div>
  );
}
