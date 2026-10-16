// Beneficios de la ficha por sección: "Puede postular ahora" y "Falta información" abiertas, "Ya postuló
// o sin cupo" plegada; filtro local (no se guarda) con conteos. Cada tarjeta muestra solo el nombre; el
// detalle (chips, estado, faltantes, preguntas de C3, dónde ir y fuentes) se abre al tocarla. El orden
// es el que entrega C3 (domain/benefitGroups.ts, FE-003): sin puntajes, posición ni urgencia en pantalla.
// DEC-072: `scopes` agrega "Disponible en su comuna" (LOCAL) y, si es SOLO DEMO, su nombre y "Solo demo".
// Al final, "Qué hacer ahora" (actionPlan.ts, determinista, sin LLM).
import { useId, useState } from 'react';
import { TERRITORIAL_COPY } from '../../api/proposals/territorial';
import type { CatalogScopeItem } from '../../api/proposals/types';
import type { AccessState } from '../../api/types';
import { isPendingWithoutCodes, visibleSections, type BenefitFilter, type BenefitRow, type BenefitSection, type BenefitSections as Sections } from '../../domain/benefitGroups';
import { formatInteger } from '../../domain/format';
import { accessPresentation, ACCESS_STATE_KEY, knownMissingLabels, LEVEL_KEY } from '../../domain/presentation';
import { t } from '../../i18n/copy';
import { ButtonLink } from '../../ui/Button';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { ChoiceChips } from '../../ui/ChoiceChips';
import { Expandable } from '../../ui/Expandable';
import { Icon } from '../../ui/icons';
import { SourceLink } from '../../ui/SourceLink';
import { EmptyState } from '../../ui/states';
import { rowMissingTexts, rowName, type ActionPlan as Plan, type Scopes } from './actionPlan';
import { FAMILY_COPY } from './familyCopy';

type Scope = CatalogScopeItem | undefined;

const SECTION_TITLE: Readonly<Record<BenefitSection, string>> = {
  apply: FAMILY_COPY.sectionApply,
  missing: FAMILY_COPY.sectionMissing,
  done: FAMILY_COPY.sectionDone,
};

/** Estado a presentar: un SI pendiente sin códigos se lee como "puede postular" (no se pide nada). */
const shownState = (row: BenefitRow): AccessState => (isPendingWithoutCodes(row) ? 'ELEGIBLE_SIN_ASIGNACION' : row.accessState);

function RowChips({ row, scope }: { readonly row: BenefitRow; readonly scope: Scope }) {
  const group = accessPresentation(shownState(row));
  return (
    <div className="flex flex-wrap gap-2">
      {group !== null && <Chip icon={group.icon} tone={group.tone} label={t(group.labelKey)} />}
      {row.level !== null && (
        <Chip icon={row.level === 'CONFIRMADO' ? 'check' : 'info'} tone={row.level === 'CONFIRMADO' ? 'neutral' : 'other'} label={t(LEVEL_KEY[row.level])} />
      )}
      {scope?.scope === 'LOCAL' && <Chip icon="home" tone="neutral" label={TERRITORIAL_COPY.localChip} />}
      {scope?.demo === true && <Chip icon="info" tone="other" label={TERRITORIAL_COPY.demoLabel} />}
    </div>
  );
}

function TextList({ label, items, c3 = false }: { readonly label: string; readonly items: readonly string[]; readonly c3?: boolean }) {
  return (
    <div>
      <p className="font-semibold">{label}</p>
      <ul className="list-disc pl-6">
        {items.map((item) => (
          <li key={item} className={c3 ? 'c3-text' : undefined}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function BenefitCard({ row, section, scope }: { readonly row: BenefitRow; readonly section: BenefitSection; readonly scope: Scope }) {
  const [open, setOpen] = useState(false);
  const regionId = useId();
  const pending = section === 'apply' ? knownMissingLabels(row.missingCodes) : [];
  const opportunity = row.opportunity;
  return (
    <li data-benefit-card className={CARD_CLASS}>
      <h3 className="c3-text">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={regionId}
          onClick={() => setOpen((value) => !value)}
          className="flex min-h-12 w-full items-center justify-between gap-2 text-left font-semibold"
        >
          {rowName(row, scope)}
          <Icon name="chevron-down" className={`size-5 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>
      </h3>
      <div id={regionId} hidden={!open} className="mt-3 space-y-3">
        <RowChips row={row} scope={scope} />
        <p className="text-ink-muted">{t(ACCESS_STATE_KEY[shownState(row)])}</p>
        {section === 'missing' && <TextList label={FAMILY_COPY.missingLabel} items={rowMissingTexts(row)} />}
        {section === 'missing' && row.questions.length > 0 && <TextList label={t('family.suggested_question_label')} items={row.questions} c3 />}
        {pending.length > 0 && (
          <p>
            <span className="font-semibold">{t('family.pending_confirm_label')}</span> {pending.join(' · ')}
          </p>
        )}
        {opportunity !== null && (
          <>
            <div>
              <p className="font-semibold">{t('card.where_label')}</p>
              <p className="c3-text">{opportunity.where_to_go ?? t('card.where_none')}</p>
            </div>
            {opportunity.sources.length > 0 && (
              <div>
                <p className="font-semibold">{t('card.sources_label')}</p>
                <ul>
                  {opportunity.sources.map((source) => (
                    <li key={source.source_id}>
                      <SourceLink citation={source} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </li>
  );
}

function RowList({ rows, section, scopes }: { readonly rows: readonly BenefitRow[]; readonly section: BenefitSection; readonly scopes: Scopes }) {
  if (rows.length === 0) return <EmptyState message={t('family.applies_empty')} />;
  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <BenefitCard key={row.benefitId} row={row} section={section} scope={scopes.get(row.benefitId)} />
      ))}
    </ul>
  );
}

export function BenefitSections({ sections, scopes }: { readonly sections: Sections; readonly scopes: Scopes }) {
  const [filter, setFilter] = useState<BenefitFilter>('all');
  const baseId = useId();
  const count = (section: BenefitSection) => formatInteger(sections[section].length);
  const options: { value: BenefitFilter; label: string }[] = [
    { value: 'all', label: FAMILY_COPY.filterAll },
    { value: 'apply', label: FAMILY_COPY.filterApply(count('apply')) },
    { value: 'missing', label: FAMILY_COPY.filterMissing(count('missing')) },
    { value: 'done', label: FAMILY_COPY.filterDone(count('done')) },
  ];
  return (
    <div className="space-y-5">
      <ChoiceChips
        legend={FAMILY_COPY.filterLegend}
        options={options}
        value={filter}
        onChange={(value) => setFilter(options.find((option) => option.value === value)?.value ?? 'all')}
      />
      {visibleSections(sections, filter).map((section) => {
        const headingId = `${baseId}-${section}`;
        const list = <RowList rows={sections[section]} section={section} scopes={scopes} />;
        return (
          <section key={section} aria-labelledby={headingId} data-benefit-section={section} className="space-y-3">
            <h2 id={headingId}>{SECTION_TITLE[section]}</h2>
            {section === 'done' && filter === 'all' ? (
              <Expandable openLabel={FAMILY_COPY.showDone} closeLabel={FAMILY_COPY.hideDone}>
                {list}
              </Expandable>
            ) : (
              list
            )}
          </section>
        );
      })}
    </div>
  );
}

/** "Qué hacer ahora": plan corto determinista con lo que ya muestra la ficha. */
export function ActionPlanSection({ plan, addInfoHref }: { readonly plan: Plan; readonly addInfoHref: string }) {
  return (
    <section aria-labelledby="family-plan" data-action-plan className={`${CARD_CLASS} space-y-3`}>
      <h2 id="family-plan">{FAMILY_COPY.planTitle}</h2>
      {plan.ask !== null && (
        <>
          <p>{plan.ask.withForm ? FAMILY_COPY.planAsk : FAMILY_COPY.planAskNoForm}</p>
          <ul className="list-disc space-y-1 pl-6">
            {plan.ask.items.map((item) => (
              <li key={item} className="c3-text">
                {item}
              </li>
            ))}
          </ul>
          {plan.ask.withForm && (
            <ButtonLink to={addInfoHref} variant="secondary" icon="plus" className="w-full">
              {t('family.actions.add_info')}
            </ButtonLink>
          )}
        </>
      )}
      {plan.deliver.length > 0 && <p className="c3-text">{FAMILY_COPY.planDeliver(plan.deliver.join(', '))}</p>}
      {plan.none && <p>{FAMILY_COPY.planNone}</p>}
    </section>
  );
}
