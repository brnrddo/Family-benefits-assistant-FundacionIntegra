// Inicio / Mi jardín (design.md §9.1, FE-001/FE-003, DEC-037): avance del jardín y TODAS las
// familias en orden NEUTRO (alfabético por nombre de trato local; sin nombre, por family_id). Ya no
// se ordena ni destaca por prioridad familiar: cada tarjeta muestra sus acciones prioritarias
// (top_benefit_ids de C3), el semáforo, el estado de conversación y el total de oportunidades, tal
// como vienen de C3. Ordenar alfabéticamente no es recalcular ranking (no usa priority_score).
import { useEffect, useId, useState } from 'react';
import { generatePath, Link } from 'react-router';
import type { FamilySummary, JardinSummary } from '../../api/types';
import { useFamilias } from '../../data/queries';
import { familyDisplayName, shortFamilyId } from '../../domain/familyName';
import { sortFamiliesNeutral } from '../../domain/familyOrder';
import { formatInteger } from '../../domain/format';
import { CONVERSATION_STATUS_KEY, TRAFFIC_LIGHT_PRESENTATION } from '../../domain/presentation';
import { benefitLabel, t } from '../../i18n/copy';
import { useQueueSummary } from '../../offline/conversationQueue';
import { useLocalNames } from '../../offline/localNames';
import { ButtonLink } from '../../ui/Button';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { DataFreshness } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, Skeleton } from '../../ui/states';
import { QueuePanel } from '../conversation/QueuePanel';
import { QuickInformButton } from '../conversation/QuickInform';
import { DEMO_COPY, greeting } from '../demo-session/demoCopy';
import { useDemoDirectory, useDemoSession, type DemoFamilyEntry } from '../demo-session/session';
import { useSelectedGarden } from '../system/useSelectedGarden';
import { GardenStats } from './GardenStats';

/** Minúsculas sin tildes, para buscar sin importar cómo se escriba. */
const fold = (text: string): string => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();

/** Búsqueda local (sin red): nombre del niño, apellido de familia o ID corto. */
function matchesFamilySearch(
  family: FamilySummary,
  query: string,
  name: string,
  entry: DemoFamilyEntry | undefined,
): boolean {
  const q = fold(query);
  if (q === '') return true;
  const haystack = [name, entry?.familyName ?? '', entry?.childName ?? '', shortFamilyId(family.family_id), family.family_id];
  return haystack.some((value) => fold(value).includes(q));
}

const familyPath = (familyId: string) => generatePath('/familias/:familyId', { familyId });
/** Tope de páginas por jardín (E-3: ~10 familias por jardín, 25 por página). */
const MAX_PAGES = 20;

interface FamilyRowProps {
  readonly family: FamilySummary;
  readonly name: string;
  /** Apellido de familia de la sesión demo ("Familia Contreras Araya"), como subtítulo. */
  readonly familyName: string | undefined;
  readonly pendingLocal: boolean;
  readonly gardenId: string;
  readonly snapshotId: string | undefined;
}

function FamilyRow({ family, name, familyName, pendingLocal, gardenId, snapshotId }: FamilyRowProps) {
  const light = TRAFFIC_LIGHT_PRESENTATION[family.traffic_light];
  return (
    <li className="space-y-2">
      <Link to={familyPath(family.family_id)} data-family-row className={`${CARD_CLASS} flex items-center gap-3 hover:border-primary`}>
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <p className="text-lg font-bold">{name}</p>
            {familyName !== undefined && <p className="text-ink-muted">{familyName}</p>}
          </div>
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
      {/* B3: un toque, fuera del enlace (sin controles anidados). Sin cola local pendiente. */}
      {snapshotId !== undefined && !pendingLocal && (
        <QuickInformButton
          familyId={family.family_id}
          gardenId={gardenId}
          benefitIds={family.top_benefit_ids}
          snapshotId={snapshotId}
          informed={family.conversation_status === 'CONVERSADA'}
        />
      )}
    </li>
  );
}

function FamilyList({ garden }: { readonly garden: JardinSummary }) {
  const familias = useFamilias(garden.garden_id);
  const queue = useQueueSummary();
  const names = useLocalNames();
  const directory = useDemoDirectory();
  const [query, setQuery] = useState('');
  const searchId = useId();
  const searchHintId = useId();
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

  const all = sortFamiliesNeutral(familias.data?.pages.flatMap((page) => page.body.items) ?? [], names);
  const items = all.filter((family) =>
    matchesFamilySearch(family, query, familyDisplayName(family.family_id, names), directory.get(family.family_id)),
  );

  return (
    <section aria-labelledby="home-list-title" className="space-y-3">
      <h2 id="home-list-title">{t('home.list_title')}</h2>
      <DataFreshness result={familias.data?.pages[0]} />
      {isFetchNextPageError && <ErrorState error={familias.error} onRetry={() => void fetchNextPage()} />}
      {all.length > 0 && (
        <div className="space-y-1">
          <label htmlFor={searchId} className="block font-semibold">
            {DEMO_COPY.searchLabel}
          </label>
          <p id={searchHintId} className="text-[0.9rem] text-ink-muted">
            {DEMO_COPY.searchHint}
          </p>
          <input
            id={searchId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-describedby={searchHintId}
            autoComplete="off"
            className="min-h-12 w-full rounded-xl border-2 border-border-strong bg-surface px-3"
          />
        </div>
      )}
      {all.length === 0 ? (
        <EmptyState message={t('empty.families')} />
      ) : items.length === 0 ? (
        <EmptyState icon="info" message={DEMO_COPY.searchEmpty} />
      ) : (
        <ul className="space-y-3">
          {items.map((family) => (
            <FamilyRow
              key={family.family_id}
              family={family}
              name={familyDisplayName(family.family_id, names)}
              familyName={directory.get(family.family_id)?.familyName}
              pendingLocal={queue.pendingFamilyIds.has(family.family_id)}
              gardenId={garden.garden_id}
              snapshotId={familias.data?.pages[0]?.body.meta.snapshot_id}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default function HomePage() {
  const { jardines, garden } = useSelectedGarden();
  const demo = useDemoSession();
  const session = demo.active ? demo.seed : null;
  return (
    <div className="space-y-5">
      <div>
        <PageTitle>{session !== null ? greeting(session.tia.display_name) : t('home.title')}</PageTitle>
        {session !== null && <p className="text-lg text-ink-muted">{session.garden.name}</p>}
      </div>
      {jardines.isPending ? (
        <Skeleton rows={3} />
      ) : jardines.isError && jardines.data === undefined ? (
        <ErrorState error={jardines.error} onRetry={() => void jardines.refetch()} />
      ) : garden === undefined ? (
        <EmptyState message={t('empty.gardens')} />
      ) : (
        <>
          <GardenStats garden={garden} />
          <ButtonLink to="/preguntar" icon="chat" className="w-full text-lg">
            {DEMO_COPY.homeChatCta}
          </ButtonLink>
          <QueuePanel />
          <FamilyList key={garden.garden_id} garden={garden} />
        </>
      )}
    </div>
  );
}
