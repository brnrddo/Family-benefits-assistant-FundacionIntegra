// Tarjeta imprimible CARD_V1 con plantilla PROPIA (design.md §11.1, FE-009). Cada string de C3 o
// del modelo entra solo como hijo de texto de React (escape normal): nunca como tag, atributo,
// clase, estilo, id ni URL. El único href sale de SourceCitation validada HTTPS (SourceLink).
import { useId } from 'react';
import type { PrintableCard } from '../../api/types';
import { formatLocalDate } from '../../domain/format';
import { t } from '../../i18n/copy';
import { now } from '../../lib/now';
import { Icon } from '../../ui/icons';
import { SourceLink } from '../../ui/SourceLink';
import { ErrorState, ReferentialNotice } from '../../ui/states';
import { contractError } from '../../api/errors';

export function PrintableCardV1({ card }: { readonly card: PrintableCard }) {
  const titleId = useId();
  // Imposible tras validar el envelope; defensa en profundidad.
  if (card.format_version !== 'CARD_V1') return <ErrorState error={contractError('createMensaje', 'schema')} />;
  return (
    <article data-print-root aria-labelledby={titleId} className="space-y-4 rounded-card border-2 border-border-strong bg-surface p-5">
      <header className="space-y-2">
        <Icon name="compass" className="size-8 text-primary" />
        <h2 id={titleId} className="c3-text">
          {card.title}
        </h2>
        <p className="c3-text">{card.introduction}</p>
      </header>
      {card.sections.map((section, index) => (
        <section key={`${index}-${section.benefit_id}`} className="space-y-2 border-t border-border pt-3">
          <h3 className="c3-text">{section.heading}</h3>
          <dl className="space-y-1">
            <dt className="font-semibold">{t('card_v1.reason_label')}</dt>
            <dd className="c3-text">{section.reason}</dd>
            <dt className="font-semibold">{t('card_v1.action_label')}</dt>
            <dd className="c3-text">{section.action}</dd>
            {section.where_to_go !== null && (
              <>
                <dt className="font-semibold">{t('card_v1.where_label')}</dt>
                <dd className="c3-text">{section.where_to_go}</dd>
              </>
            )}
          </dl>
          {section.sources.length > 0 && (
            <div>
              <p className="font-semibold">{t('card_v1.sources_label')}</p>
              <ul>
                {section.sources.map((source) => (
                  <li key={source.source_id}>
                    <SourceLink citation={source} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      ))}
      <footer className="space-y-2 border-t border-border pt-3">
        <ReferentialNotice />
        <p className="text-[0.9rem] text-ink-muted">{t('card_v1.printed_on', { date: formatLocalDate(now()) })}</p>
      </footer>
    </article>
  );
}
