// Ficha familia (design.md §9.2, FE-001/FE-003/FE-004): espacio vacío reservado al agente (Tarea 7, B),
// tarjeta "Datos del hogar" (quiénes viven, tramo,
// datos por confirmar y "Agregar información" ahí mismo), las acciones prioritarias (top tres en el orden
// de C3, chips, “por qué”, detalle expandible), los beneficios relevantes, plegados tras "Ver todos los
// beneficios", en dos grupos ("Beneficios que
// aplica" / "Falta información", tal como vienen de C3; la ficha ya no trae NO/NO_APLICA, DEC-070), con
// chip "Disponible en su comuna"/"Solo demo" si hay alcance (DEC-072), "Preguntar a la familia" sin
// repetidos, aviso y fuentes. El cambio de orden pide a C3; el cliente no reordena. Señales de
// urgencia/vulnerabilidad del contexto no se muestran (SUP-032). El título es el nombre de trato
// local (DEC-038) o un genérico con el ID corto; la URL y los requests usan el family_id de C3.
import { useEffect, useMemo } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { CatalogScopeItem } from '../../api/proposals/types';
import type { FamilyContextView, FamilyDetail, Opportunity, OpportunityOrder } from '../../api/types';
import { runtimeConfig } from '../../config/profile';
import { useCatalogoAlcance, useContexto, useFamilia, useOportunidades } from '../../data/queries';
import { familyMissingCodes, uniqueTexts } from '../../domain/benefitGroups';
import { familyDisplayName } from '../../domain/familyName';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
import { FORMAT_KEY, INCONSISTENCY_KEY, missingCodeLabels, ORDER_KEY, ROLE_KEY } from '../../domain/presentation';
import { t, yearsLabel } from '../../i18n/copy';
import { useLocalNames } from '../../offline/localNames';
import { Button, ButtonLink } from '../../ui/Button';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { DataFreshness } from '../../ui/DataStatus';
import { Expandable } from '../../ui/Expandable';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { Banner, EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { QuickInformButton } from '../conversation/QuickInform';
import NotFoundPage from '../system/NotFoundPage';
import { BenefitGroups } from './BenefitGroups';
import { FAMILY_COPY } from './familyCopy';
import { NameEditor } from './NameEditor';
import { OpportunityCard } from './OpportunityCard';
import { familyRoutes } from './routes';

const ORDERS: readonly OpportunityOrder[] = ['prioridad', 'urgencia', 'beneficio'];
const MAX_CARDS = 3;
const NO_NAMES: ReadonlyMap<string, string> = new Map();
const NO_SCOPES: ReadonlyMap<string, CatalogScopeItem> = new Map();

function parseOrder(raw: string | null): OpportunityOrder {
  return ORDERS.find((order) => order === raw) ?? 'prioridad';
}

/** "Datos del hogar": quiénes viven, tramo, datos por confirmar y el botón "Agregar información" ahí mismo. */
function HouseholdCard({
  detail,
  context,
  addInfoHref,
}: {
  readonly detail: FamilyDetail;
  readonly context: FamilyContextView | null;
  /** null = sin la capacidad o sin datos faltantes: no hay botón. */
  readonly addInfoHref: string | null;
}) {
  const toConfirm = missingCodeLabels([...(context?.missing_codes ?? []), ...familyMissingCodes(detail)]);
  return (
    <section aria-labelledby="family-household" className={`${CARD_CLASS} space-y-3`}>
      <h2 id="family-household">{ADD_INFO_COPY.householdTitle}</h2>
      <Chip
        icon={detail.informed ? 'check' : 'clock'}
        tone={detail.informed ? 'go' : 'neutral'}
        label={detail.informed ? t('family.informed_yes') : t('family.informed_no')}
      />
      <h3>{t('family.composition_title')}</h3>
      <ul className="flex flex-wrap gap-2">
        {detail.composition.map((member, index) => (
          <li key={`${member.role}-${index}`} className="inline-flex items-center gap-1.5 rounded-xl bg-canvas px-3 py-1">
            <Icon name={member.role === 'CHILD' ? 'child' : 'user'} className="size-5 text-ink-muted" />
            {t(ROLE_KEY[member.role])} · {yearsLabel(member.age, formatInteger(member.age))}
          </li>
        ))}
      </ul>
      <p>{detail.rsh_band === null ? t('family.rsh_none') : t('family.rsh', { band: formatInteger(detail.rsh_band) })}</p>
      <h3>{t('family.to_confirm_title')}</h3>
      {toConfirm.length === 0 ? (
        <p>{t('common.not_available')}</p>
      ) : (
        <ul className="list-disc space-y-1 pl-6">
          {toConfirm.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      )}
      {context !== null && (
        <div className="space-y-1 text-ink-muted">
          <p>
            {t('family.preferred_format_label')}: {t(FORMAT_KEY[context.preferred_format])}
          </p>
          {context.preferred_format === 'AUDIO' && <p>{t('a11y.audio_unavailable')}</p>}
          {!context.language.startsWith('es') && (
            <p>
              {t('family.language_note', { language: context.language })} {t('message.translation_unavailable')}
            </p>
          )}
        </div>
      )}
      {addInfoHref !== null && (
        <ButtonLink to={addInfoHref} variant="secondary" icon="plus" className="w-full">
          {t('family.actions.add_info')}
        </ButtonLink>
      )}
    </section>
  );
}

/** "Preguntar a la familia": preguntas de las tarjetas visibles e inconsistencias, sin repetidos. */
function AskSection({ cards, context }: { readonly cards: readonly Opportunity[]; readonly context: FamilyContextView | null }) {
  const questions = uniqueTexts(cards.flatMap((card) => card.suggested_questions));
  const inconsistencies = uniqueTexts((context?.inconsistency_codes ?? []).map((code) => t(INCONSISTENCY_KEY[code])));
  return (
    <section aria-labelledby="family-ask" className="space-y-2">
      <h2 id="family-ask">{t('family.ask_title')}</h2>
      <ul className="list-disc space-y-1 pl-6">
        {questions.map((question) => (
          <li key={question} className="c3-text">
            {question}
          </li>
        ))}
        {inconsistencies.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
    </section>
  );
}

function FamilyView({ familyId }: { readonly familyId: string }) {
  const { capabilities, profile } = runtimeConfig();
  const location = useLocation();
  const names = useLocalNames();
  const [search, setSearch] = useSearchParams();
  const rawOrder = search.get('orden');
  const order = parseOrder(rawOrder);
  const ficha = useFamilia(familyId);
  const prioridad = useOportunidades(familyId, 'prioridad', ficha.isSuccess);
  const ordered = useOportunidades(familyId, order, ficha.isSuccess && order !== 'prioridad');
  const contexto = useContexto(familyId, ficha.isSuccess);
  // DEC-072: sin flag, o si la propuesta falla, la ficha se ve igual (nunca bloquea).
  const alcance = useCatalogoAlcance(capabilities.territorial && ficha.isSuccess);
  const alcanceItems = capabilities.territorial ? alcance.data?.body.items : undefined;
  const scopes = useMemo(
    () => (alcanceItems === undefined ? NO_SCOPES : new Map(alcanceItems.map((item) => [item.benefit_id, item]))),
    [alcanceItems],
  );
  // Estado de navegación en memoria (nunca en la URL): vuelve de "Agregar información" con éxito.
  const addInfoDone = (location.state as { addInfoDone?: unknown } | null)?.addInfoDone === true;

  useEffect(() => {
    if (rawOrder !== null && rawOrder !== order) {
      setSearch(
        (params) => {
          params.delete('orden');
          return params;
        },
        { replace: true },
      );
    }
  }, [rawOrder, order, setSearch]);

  const changeOrder = (value: string) =>
    setSearch(
      (params) => {
        if (value === 'prioridad') params.delete('orden');
        else params.set('orden', value);
        return params;
      },
      { replace: true },
    );

  const title = familyDisplayName(familyId, names);
  // La pestaña/historial nunca lleva el nombre de trato: siempre el genérico con el ID corto.
  const tabTitle = familyDisplayName(familyId, NO_NAMES);
  if (ficha.isPending) {
    return (
      <div className="space-y-4">
        <PageTitle documentTitle={tabTitle}>{title}</PageTitle>
        <Skeleton rows={4} rowClass="h-28" />
      </div>
    );
  }
  if (ficha.isError && ficha.data === undefined) {
    return (
      <div className="space-y-4">
        <PageTitle documentTitle={tabTitle}>{title}</PageTitle>
        <ErrorState
          error={ficha.error}
          onRetry={() => void ficha.refetch()}
          action={
            <ButtonLink to="/" variant="ghost" icon="home">
              {t('notfound.back_home')}
            </ButtonLink>
          }
        />
      </div>
    );
  }

  const detail = ficha.data.body.data;
  // Con `prioridad` se usan los top_opportunities de la ficha; con otro orden, los 3 primeros de C3.
  const cards: readonly Opportunity[] = order === 'prioridad' ? detail.top_opportunities : (ordered.data?.body.items ?? []).slice(0, MAX_CARDS);
  const resultOf = (benefitId: string) => detail.benefit_results.find((r) => r.benefit_id === benefitId);
  const homeLink = `/?${new URLSearchParams({ jardin: detail.garden_id }).toString()}`;
  const hasOpportunities = detail.top_opportunities.length > 0;
  const showAddInfo = capabilities.addInfo && familyMissingCodes(detail).length > 0;
  const context = contexto.data?.body.data ?? null;
  // Slot del agente: lo monta B (features/assistant/) en la Tarea 7
  const assistantSlot = <div data-assistant-slot className="empty:hidden" />;

  return (
    <div className="space-y-5">
      <ButtonLink to={homeLink} variant="ghost" icon="chevron-left" className="-ml-3">
        {t('nav.back')}
      </ButtonLink>
      <PageTitle documentTitle={tabTitle}>{title}</PageTitle>
      {capabilities.localNames && <NameEditor familyId={familyId} />}
      {addInfoDone && (
        <Banner tone="info" icon="check">
          {t('family.add_info_done')}
        </Banner>
      )}
      <DataFreshness result={ficha.data} />

      {/* Bloques de la ficha (plan de demo §7.1 #5): agente → "Datos del hogar" → acciones → lista plegada. */}
      {assistantSlot}

      <HouseholdCard detail={detail} context={context} addInfoHref={showAddInfo ? familyRoutes.agregarInformacion(familyId) : null} />

      <section aria-labelledby="family-top" className="space-y-3">
        <h2 id="family-top">{t('family.top_title')}</h2>
        <ChoiceChips
          legend={t('family.order_label')}
          options={ORDERS.map((value) => ({ value, label: t(ORDER_KEY[value]) }))}
          value={order}
          onChange={changeOrder}
        />
        {order !== 'prioridad' && ordered.isPending ? (
          <Skeleton rows={3} rowClass="h-40" />
        ) : order !== 'prioridad' && ordered.isError ? (
          <ErrorState error={ordered.error} onRetry={() => void ordered.refetch()} />
        ) : cards.length === 0 ? (
          <EmptyState message={t('empty.opportunities')} />
        ) : (
          <div className="space-y-4">
            {cards.map((card) => (
              <OpportunityCard key={card.benefit_id} opportunity={card} result={resultOf(card.benefit_id)} />
            ))}
          </div>
        )}
      </section>

      {/* Lista secundaria, plegada por defecto; el orden dentro de cada grupo es el de C3 (no se reordena). */}
      <Expandable openLabel={FAMILY_COPY.showAllBenefits} closeLabel={FAMILY_COPY.hideAllBenefits}>
        {/* "Compartir beneficios" es solo para la demo: oculto en `escala` (mismo criterio que Familia nueva). */}
        <BenefitGroups detail={detail} opportunities={prioridad.data?.body.items ?? []} scopes={scopes} showShare={profile !== 'escala'} />
      </Expandable>

      <AskSection cards={cards} context={context} />

      <ReferentialNotice />

      <div className="sticky bottom-18 z-10 flex flex-col gap-2 rounded-card bg-canvas/95 py-2">
        {hasOpportunities ? (
          <>
            {/* B3 (DEC-080): un toque con los beneficios recién mostrados; el flujo de 3 toques sigue. */}
            <QuickInformButton
              familyId={familyId}
              gardenId={detail.garden_id}
              benefitIds={detail.top_opportunities.map((o) => o.benefit_id)}
              snapshotId={ficha.data.body.meta.snapshot_id}
              informed={detail.informed}
            />
            <ButtonLink to={familyRoutes.conversacion(familyId)} icon="check" data-primary-action className="w-full">
              {t('family.actions.mark')}
            </ButtonLink>
          </>
        ) : (
          <>
            <Button icon="check" disabled className="w-full">
              {t('family.actions.mark')}
            </Button>
            <p className="text-center text-ink-muted">{t('conversation.no_benefits')}</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function FamilyPage() {
  const { familyId } = useParams();
  if (!isValidId(familyId)) return <NotFoundPage />;
  return <FamilyView key={familyId} familyId={familyId} />;
}
