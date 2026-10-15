// Inicio / Mi jardín (design.md §9.1, FE-001/FE-003): avance y lista de familias TAL COMO vienen
// de C3 (orden, conteos, porcentaje y semáforo); la vista no ordena, filtra ni calcula.
import { generatePath, Link } from 'react-router';
import type { FamilySummary, JardinSummary } from '../../api/types';
import { useFamilias } from '../../data/queries';
import { formatInteger, formatPercent } from '../../domain/format';
import { CONVERSATION_STATUS_KEY, TRAFFIC_LIGHT_PRESENTATION, ZONE_KEY } from '../../domain/presentation';
import { t } from '../../i18n/copy';
import { useQueueSummary } from '../../offline/conversationQueue';
import { Button, ButtonLink } from '../../ui/Button';
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

function FamilyRow({ family, pendingLocal }: { readonly family: FamilySummary; readonly pendingLocal: boolean }) {
  const light = TRAFFIC_LIGHT_PRESENTATION[family.traffic_light];
  return (
    <li>
      <Link to={familyPath(family.family_id)} className={`${CARD_CLASS} flex items-center gap-3 hover:border-primary`}>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="font-bold">{t('home.family_item', { family_id: family.family_id })}</p>
          <div className="flex flex-wrap gap-2">
            <Chip icon={light.icon} tone={light.tone} label={t(light.labelKey)} />
            {pendingLocal && <Chip icon="clock" tone="ask" label={t('home.pending_local')} />}
          </div>
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
  const items = familias.data?.pages.flatMap((page) => page.body.items) ?? [];
  // Primera PENDIENTE en el orden de C3 que no esté ya en la cola local (§9.1).
  const next = items.find((f) => f.conversation_status === 'PENDIENTE' && !queue.pendingFamilyIds.has(f.family_id));

  if (familias.isPending) return <Skeleton rows={5} />;
  if (familias.isError && familias.data === undefined) {
    return <ErrorState error={familias.error} onRetry={() => void familias.refetch()} />;
  }

  return (
    <>
      <Card className="space-y-3">
        <h2>{t('home.next_family')}</h2>
        {next !== undefined ? (
          <ButtonLink to={familyPath(next.family_id)} icon="user" data-primary-action className="w-full">
            {t('home.family_item', { family_id: next.family_id })}
          </ButtonLink>
        ) : (
          <p>{t('home.next_family_none')}</p>
        )}
      </Card>
      <section aria-labelledby="home-list-title" className="space-y-3">
        <h2 id="home-list-title">{t('home.list_title')}</h2>
        <DataFreshness result={familias.data?.pages[0]} />
        {items.length === 0 ? (
          <EmptyState message={t('empty.families')} />
        ) : (
          <ol className="space-y-3">
            {items.map((family) => (
              <FamilyRow key={family.family_id} family={family} pendingLocal={queue.pendingFamilyIds.has(family.family_id)} />
            ))}
          </ol>
        )}
        {familias.isFetchNextPageError && <ErrorState error={familias.error} onRetry={() => void familias.fetchNextPage()} />}
        {familias.hasNextPage && (
          <Button variant="secondary" className="w-full" busy={familias.isFetchingNextPage} onClick={() => void familias.fetchNextPage()}>
            {t('common.load_more')}
          </Button>
        )}
      </section>
    </>
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
