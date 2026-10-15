// Tarjeta de oportunidad (design.md §9.2): chips de grupo, urgencia, beneficio y acción; “¿Por qué
// está primero?” siempre visible; detalle expandible con dónde ir, faltantes, fuentes y detalle técnico.
// Los chips solo traducen enums/valores de C3 a ícono + texto (SUP-036); no cambian el orden.
import { useId } from 'react';
import type { BenefitResult, MissingCode, Opportunity } from '../../api/types';
import { formatClp, formatInteger } from '../../domain/format';
import { accessPresentation, ACCESS_STATE_KEY, ACTION_TYPE_KEY, MISSING_CODE_KEY, urgencyChip } from '../../domain/presentation';
import { t } from '../../i18n/copy';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { Expandable } from '../../ui/Expandable';
import { SourceLink } from '../../ui/SourceLink';
import { TechnicalDetail } from './TechnicalDetail';

const isMissingCode = (code: string): code is MissingCode => Object.prototype.hasOwnProperty.call(MISSING_CODE_KEY, code);

function amountLabel(opportunity: Opportunity): string {
  if (opportunity.estimated_annual_amount === null) return t('chip.benefit.no_amount');
  const amount = t('chip.benefit.amount', { amount: formatClp(opportunity.estimated_annual_amount) });
  return opportunity.benefit_estimated ? `${amount} ${t('chip.benefit.estimated')}` : amount;
}

export interface OpportunityCardProps {
  readonly opportunity: Opportunity;
  readonly result: BenefitResult | undefined;
}

export function OpportunityCard({ opportunity, result }: OpportunityCardProps) {
  const headingId = useId();
  const group = accessPresentation(opportunity.access_state);
  const urgency = urgencyChip(opportunity.urgency);
  const missing = opportunity.missing_codes.filter(isMissingCode);
  return (
    <article aria-labelledby={headingId} className={`${CARD_CLASS} space-y-3`}>
      <p className="text-[0.9rem] text-ink-muted">{t('card.position', { position: formatInteger(opportunity.position) })}</p>
      <h3 id={headingId} className="c3-text">
        {opportunity.simple_title}
      </h3>
      <ul className="flex flex-wrap gap-2">
        {group !== null && (
          <li>
            <Chip icon={group.icon} tone={group.tone} label={t(group.labelKey)} />
          </li>
        )}
        {urgency !== null && (
          <li>
            <Chip icon="clock" tone="ask" label={t(urgency)} />
          </li>
        )}
        <li>
          <Chip icon="coins" tone="neutral" label={amountLabel(opportunity)} />
        </li>
        <li>
          <Chip icon="chat" tone="neutral" label={t(ACTION_TYPE_KEY[opportunity.action_type])} />
        </li>
        {opportunity.level === 'PRELIMINAR' && (
          <li>
            <Chip icon="info" tone="other" label={t('level.preliminar')} />
          </li>
        )}
      </ul>
      <p className="text-ink-muted">{t(ACCESS_STATE_KEY[opportunity.access_state])}</p>
      <div className="rounded-xl bg-canvas p-3">
        <p className="font-semibold">{t('card.why_first_label')}</p>
        <p className="c3-text">{opportunity.why_first}</p>
      </div>
      <Expandable openLabel={t('card.expand')} closeLabel={t('card.collapse')}>
        <div>
          <h4 className="font-semibold">{t('card.where_label')}</h4>
          <p className="c3-text">{opportunity.where_to_go ?? t('card.where_none')}</p>
        </div>
        {missing.length > 0 && (
          <div>
            <h4 className="font-semibold">{t('card.missing_label')}</h4>
            <ul className="list-disc pl-6">
              {missing.map((code) => (
                <li key={code}>{t(MISSING_CODE_KEY[code])}</li>
              ))}
            </ul>
          </div>
        )}
        {opportunity.sources.length > 0 && (
          <div>
            <h4 className="font-semibold">{t('card.sources_label')}</h4>
            <ul>
              {opportunity.sources.map((source) => (
                <li key={source.source_id}>
                  <SourceLink citation={source} />
                </li>
              ))}
            </ul>
          </div>
        )}
        <Expandable openLabel={t('tech.open')} closeLabel={t('card.collapse')}>
          <TechnicalDetail opportunity={opportunity} result={result} />
        </Expandable>
      </Expandable>
    </article>
  );
}
