// Ficha familia (design.md §9.2, FE-001/FE-003/FE-004), de arriba abajo: "Preguntas tipo" del agente
// (FamilyQuickQuestions de B, Tarea 7); "Datos del hogar" plegada (quiénes viven, tramo, datos por confirmar concretos y
// "Agregar información"); filtro "Todos · Aplica · Falta info · Ya postuló o sin cupo" con conteos;
// secciones "Puede postular ahora" y "Falta información" abiertas y "Ya postuló o sin cupo" plegada
// (BenefitSections.tsx), con tarjetas que muestran solo el nombre y abren el detalle; y "Qué hacer
// ahora" (actionPlan.ts, determinista, sin LLM). El orden es el de C3 `prioridad` (el cliente no
// reordena ni muestra puntajes). Señales de urgencia/vulnerabilidad del contexto no se muestran
// (SUP-032). El título es el nombre de trato local (DEC-038) o un genérico con el ID corto; la URL y
// los requests usan el family_id de C3.
import { useId, useMemo, useState } from 'react';
import { useLocation, useParams } from 'react-router';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { CatalogScopeItem } from '../../api/proposals/types';
import type { FamilyContextView, FamilyDetail } from '../../api/types';
import { runtimeConfig } from '../../config/profile';
import { useCatalogoAlcance, useContexto, useFamilia, useOportunidades } from '../../data/queries';
import { benefitSections, familyMissingCodes } from '../../domain/benefitGroups';
import { familyDisplayName } from '../../domain/familyName';
import { formatInteger } from '../../domain/format';
import { isValidId } from '../../domain/ids';
import { FORMAT_KEY, ROLE_KEY } from '../../domain/presentation';
import { t, yearsLabel } from '../../i18n/copy';
import { useLocalNames } from '../../offline/localNames';
import { Button, ButtonLink } from '../../ui/Button';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { DataFreshness } from '../../ui/DataStatus';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { Banner, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { FamilyQuickQuestions } from '../assistant/FamilyQuickQuestions';
import { QuickInformButton } from '../conversation/QuickInform';
import NotFoundPage from '../system/NotFoundPage';
import { buildActionPlan, toConfirmItems } from './actionPlan';
import { ActionPlanSection, BenefitSections } from './BenefitSections';
import { NameEditor } from './NameEditor';
import { familyRoutes } from './routes';

const NO_NAMES: ReadonlyMap<string, string> = new Map();
const NO_SCOPES: ReadonlyMap<string, CatalogScopeItem> = new Map();

/** "Datos del hogar", plegada: quiénes viven, tramo, datos por confirmar y "Agregar información". */
function HouseholdCard({
  detail,
  context,
  toConfirm,
  addInfoHref,
}: {
  readonly detail: FamilyDetail;
  readonly context: FamilyContextView | null;
  readonly toConfirm: readonly string[];
  /** null = sin la capacidad o sin datos faltantes: no hay botón. */
  readonly addInfoHref: string | null;
}) {
  const [open, setOpen] = useState(false);
  const regionId = useId();
  return (
    <section aria-labelledby="family-household" data-household className={CARD_CLASS}>
      <h2 id="family-household">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={regionId}
          onClick={() => setOpen((value) => !value)}
          className="flex min-h-12 w-full items-center justify-between gap-2 text-left"
        >
          {ADD_INFO_COPY.householdTitle}
          <Icon name="chevron-down" className={`size-5 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>
      </h2>
      <div id={regionId} hidden={!open} className="mt-4 space-y-4">
        <Chip
          icon={detail.informed ? 'check' : 'clock'}
          tone={detail.informed ? 'go' : 'neutral'}
          label={detail.informed ? t('family.informed_yes') : t('family.informed_no')}
        />
        <div className="space-y-2">
          <h3>{t('family.composition_title')}</h3>
          <ul className="flex flex-wrap gap-3">
            {detail.composition.map((member, index) => (
              <li key={`${member.role}-${index}`} className="inline-flex items-center gap-1.5 rounded-xl bg-canvas px-3 py-1.5">
                <Icon name={member.role === 'CHILD' ? 'child' : 'user'} className="size-5 text-ink-muted" />
                {t(ROLE_KEY[member.role])} · {yearsLabel(member.age, formatInteger(member.age))}
              </li>
            ))}
          </ul>
        </div>
        <p>{detail.rsh_band === null ? t('family.rsh_none') : t('family.rsh', { band: formatInteger(detail.rsh_band) })}</p>
        <div className="space-y-2">
          <h3>{t('family.to_confirm_title')}</h3>
          {toConfirm.length === 0 ? (
            <p>{t('common.not_available')}</p>
          ) : (
            <ul className="list-disc space-y-1.5 pl-6">
              {toConfirm.map((label) => (
                <li key={label} className="c3-text">
                  {label}
                </li>
              ))}
            </ul>
          )}
        </div>
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
      </div>
    </section>
  );
}

function FamilyView({ familyId }: { readonly familyId: string }) {
  const { capabilities } = runtimeConfig();
  const location = useLocation();
  const names = useLocalNames();
  const ficha = useFamilia(familyId);
  const prioridad = useOportunidades(familyId, 'prioridad', ficha.isSuccess);
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
  // Secciones en el orden de C3 `prioridad`; mientras carga, el de `top_opportunities`.
  const sections = benefitSections(detail, prioridad.data?.body.items ?? []);
  const homeLink = `/?${new URLSearchParams({ jardin: detail.garden_id }).toString()}`;
  const hasOpportunities = detail.top_opportunities.length > 0;
  const showAddInfo = capabilities.addInfo && familyMissingCodes(detail).length > 0;
  const addInfoHref = familyRoutes.agregarInformacion(familyId);
  const context = contexto.data?.body.data ?? null;
  const plan = buildActionPlan(sections, { canAddInfo: showAddInfo, scopes });

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

      {/* Bloques de la ficha: agente → "Datos del hogar" → filtro y secciones → "Qué hacer ahora". */}
      <FamilyQuickQuestions familyId={familyId} />

      <HouseholdCard
        detail={detail}
        context={context}
        toConfirm={toConfirmItems(sections, context, scopes)}
        addInfoHref={showAddInfo ? addInfoHref : null}
      />

      <BenefitSections sections={sections} scopes={scopes} />

      <ActionPlanSection plan={plan} addInfoHref={addInfoHref} />

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
