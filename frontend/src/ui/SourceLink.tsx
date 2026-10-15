// Enlace a una fuente (design.md §11.3, FE-009): el ÚNICO href dinámico sale de una
// SourceCitation tipada y validada como HTTPS. Si la URL no pasa, se muestra el source_id como texto.
import type { SourceCitation } from '../api/types';
import { toSafeHttpsUrl } from '../domain/safeUrl';
import { t } from '../i18n/copy';
import { Icon } from './icons';

export function SourceLink({ citation }: { readonly citation: SourceCitation }) {
  const href = toSafeHttpsUrl(citation.url);
  const label = t('card.source_link', { source_id: citation.source_id });
  if (href === null) return <span className="inline-flex min-h-11 items-center">{label}</span>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer external"
      referrerPolicy="no-referrer"
      className="inline-flex min-h-11 items-center gap-2 font-semibold text-primary underline underline-offset-4"
    >
      <Icon name="external" className="size-5" />
      {label}
      <span className="sr-only">{t('a11y.external_link')}</span>
    </a>
  );
}
