// Ficha familia (design.md §9.2, FE-001/FE-003/FE-004): top tres en el orden de C3, chips, “por qué”,
// detalle expandible, preguntas, datos por confirmar, aviso y fuentes. El cambio de orden pide a C3;
// el cliente no reordena. Señales de urgencia/vulnerabilidad del contexto no se muestran (SUP-032).
import { useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router';
import type { FamilyContextView, FamilyDetail, Opportunity, OpportunityOrder } from '../../api/types';
import { useContexto, useFamilia, useOportunidades } from '../../data/queries';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
import {
  accessPresentation,
  FORMAT_KEY,
  INCONSISTENCY_KEY,
  MISSING_CODE_KEY,
  ORDER_KEY,
  ROLE_KEY,
} from '../../domain/presentation';
import { t } from '../../i18n/copy';
import { Button, ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { DataFreshness } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import NotFoundPage from '../system/NotFoundPage';
import { OpportunityCard } from './OpportunityCard';
import { familyRoutes } from './routes';

const ORDERS: readonly OpportunityOrder[] = ['prioridad', 'urgencia', 'beneficio'];
const MAX_CARDS = 3;

function parseOrder(raw: string | null): OpportunityOrder {
  return ORDERS.find((order) => order === raw) ?? 'prioridad';
}

function FamilyHeader({ detail }: { readonly detail: FamilyDetail }) {
  return (
    <Card className="space-y-3">
      <Chip
        icon={detail.informed ? 'check' : 'clock'}
        tone={detail.informed ? 'go' : 'neutral'}
        label={detail.informed ? t('family.informed_yes') : t('family.informed_no')}
      />
      <h2>{t('family.composition_title')}</h2>
      <ul className="flex flex-wrap gap-2">
        {detail.composition.map((member, index) => (
          <li key={`${member.role}-${index}`} className="inline-flex items-center gap-1.5 rounded-xl bg-canvas px-3 py-1">
            <Icon name={member.role === 'CHILD' ? 'child' : 'user'} className="size-5 text-ink-muted" />
            {t(ROLE_KEY[member.role])} · {t('common.years', { age: formatInteger(member.age) })}
          </li>
        ))}
      </ul>
      <p>{detail.rsh_band === null ? t('family.rsh_none') : t('family.rsh', { band: formatInteger(detail.rsh_band) })}</p>
    </Card>
  );
}

function ContextSections({ cards, context }: { readonly cards: readonly Opportunity[]; readonly context: FamilyContextView | null }) {
  // Preguntas de las tarjetas visibles sin duplicados exactos, en orden de aparición.
  const questions = [...new Set(cards.flatMap((card) => card.suggested_questions))];
  return (
    <>
      <section aria-labelledby="family-ask" className="space-y-2">
        <h2 id="family-ask">{t('family.ask_title')}</h2>
        <ul className="list-disc space-y-1 pl-6">
          {questions.map((question) => (
            <li key={question} className="c3-text">
              {question}
            </li>
          ))}
          {context?.inconsistency_codes.map((code) => <li key={code}>{t(INCONSISTENCY_KEY[code])}</li>)}
        </ul>
      </section>
      <section aria-labelledby="family-confirm" className="space-y-2">
        <h2 id="family-confirm">{t('family.to_confirm_title')}</h2>
        {context === null ? (
          <p>{t('common.not_available')}</p>
        ) : context.missing_codes.length === 0 ? (
          <p>{t('common.not_available')}</p>
        ) : (
          <ul className="list-disc space-y-1 pl-6">
            {context.missing_codes.map((code) => (
              <li key={code}>{t(MISSING_CODE_KEY[code])}</li>
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
      </section>
    </>
  );
}

function FamilyView({ familyId }: { readonly familyId: string }) {
  const [search, setSearch] = useSearchParams();
  const rawOrder = search.get('orden');
  const order = parseOrder(rawOrder);
  const ficha = useFamilia(familyId);
  const prioridad = useOportunidades(familyId, 'prioridad', ficha.isSuccess);
  const ordered = useOportunidades(familyId, order, ficha.isSuccess && order !== 'prioridad');
  const contexto = useContexto(familyId, ficha.isSuccess);

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

  const title = t('family.title', { family_id: familyId });
  if (ficha.isPending) {
    return (
      <div className="space-y-4">
        <PageTitle>{title}</PageTitle>
        <Skeleton rows={4} rowClass="h-28" />
      </div>
    );
  }
  if (ficha.isError && ficha.data === undefined) {
    return (
      <div className="space-y-4">
        <PageTitle>{title}</PageTitle>
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
  const shown = new Set(cards.map((card) => card.benefit_id));
  const hasIt = (prioridad.data?.body.items ?? []).filter(
    (o) => (o.access_state === 'ASIGNADO' || o.access_state === 'GESTION_EN_CURSO') && !shown.has(o.benefit_id),
  );
  const resultOf = (benefitId: string) => detail.benefit_results.find((r) => r.benefit_id === benefitId);
  const homeLink = `/?${new URLSearchParams({ jardin: detail.garden_id }).toString()}`;
  const hasOpportunities = detail.top_opportunities.length > 0;

  return (
    <div className="space-y-5">
      <ButtonLink to={homeLink} variant="ghost" icon="chevron-left" className="-ml-3">
        {t('nav.back')}
      </ButtonLink>
      <PageTitle>{title}</PageTitle>
      <DataFreshness result={ficha.data} />
      <FamilyHeader detail={detail} />

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

      <ContextSections cards={cards} context={contexto.data?.body.data ?? null} />

      {hasIt.length > 0 && (
        <section aria-labelledby="family-has" className="space-y-2">
          <h2 id="family-has">{t('family.has_title')}</h2>
          <ul className="space-y-2">
            {hasIt.map((o) => {
              const p = accessPresentation(o.access_state);
              return (
                <li key={o.benefit_id} className="flex flex-wrap items-center gap-2">
                  <span className="c3-text font-semibold">{o.simple_title}</span>
                  {p !== null && <Chip icon={p.icon} tone={p.tone} label={t(p.labelKey)} />}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {hasOpportunities && (
        <div className="flex flex-col gap-2 sm:flex-row">
          <ButtonLink to={familyRoutes.guion(familyId)} variant="secondary" icon="document">
            {t('family.actions.script')}
          </ButtonLink>
          <ButtonLink to={familyRoutes.mensaje(familyId)} variant="secondary" icon="chat">
            {t('family.actions.message')}
          </ButtonLink>
        </div>
      )}

      <ReferentialNotice />

      <div className="sticky bottom-18 z-10 rounded-card bg-canvas/95 py-2">
        {hasOpportunities ? (
          <ButtonLink to={familyRoutes.conversacion(familyId)} icon="check" data-primary-action className="w-full">
            {t('family.actions.mark')}
          </ButtonLink>
        ) : (
          <>
            <Button icon="check" disabled className="w-full">
              {t('family.actions.mark')}
            </Button>
            <p className="mt-1 text-center text-ink-muted">{t('conversation.no_benefits')}</p>
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
