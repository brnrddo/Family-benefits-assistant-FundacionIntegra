// Estados de datos (FE-005, design.md §6.5): skeleton, vacío, error y avisos.
// ErrorState nunca muestra el message del servidor: solo la clave error.* y el request_id.
import type { ReactNode } from 'react';
import { errorCopyKey, helpCodeOf, isRetryableError } from '../domain/errorCopy';
import { t } from '../i18n/copy';
import { Button } from './Button';
import { CARD_CLASS } from './Card';
import { Icon, type UiIconName } from './icons';

export function Skeleton({ rows = 3, rowClass = 'h-20' }: { readonly rows?: number; readonly rowClass?: string }) {
  return (
    <div role="status" aria-busy="true" className="space-y-3">
      <span className="sr-only">{t('app.loading')}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} aria-hidden="true" className={`animate-pulse rounded-card bg-neutral-bg ${rowClass}`} />
      ))}
    </div>
  );
}

export function EmptyState({ message, icon = 'compass', action }: { readonly message: string; readonly icon?: UiIconName; readonly action?: ReactNode }) {
  return (
    <div className={`${CARD_CLASS} flex flex-col items-center gap-3 text-center`}>
      <Icon name={icon} className="size-10 text-accent" />
      <p>{message}</p>
      {action}
    </div>
  );
}

export interface ErrorStateProps {
  readonly error: unknown;
  readonly onRetry?: () => void;
  readonly action?: ReactNode;
}

export function ErrorState({ error, onRetry, action }: ErrorStateProps) {
  const helpCode = helpCodeOf(error);
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-card border border-danger-ink bg-danger-bg p-5 text-danger-ink">
      <p className="flex items-center gap-2 font-bold">
        <Icon name="alert" className="size-6" />
        {t('error.generic.title')}
      </p>
      <p>{t(errorCopyKey(error))}</p>
      {helpCode !== null && <p className="text-sm">{t('error.help_code', { request_id: helpCode })}</p>}
      <div className="flex flex-wrap gap-2">
        {onRetry !== undefined && isRetryableError(error) && (
          <Button variant="secondary" icon="refresh" onClick={onRetry}>
            {t('common.retry')}
          </Button>
        )}
        {action}
      </div>
    </div>
  );
}

export type BannerTone = 'info' | 'warn' | 'danger';

const BANNER_TONE: Readonly<Record<BannerTone, string>> = {
  info: 'bg-has-bg text-has-ink',
  warn: 'bg-ask-bg text-ask-ink',
  danger: 'bg-danger-bg text-danger-ink',
};

export function Banner({ tone = 'info', icon = 'info', children }: { readonly tone?: BannerTone; readonly icon?: UiIconName; readonly children: ReactNode }) {
  return (
    <div role="status" className={`flex items-start gap-2 px-4 py-2 ${BANNER_TONE[tone]}`}>
      <Icon name={icon} className="mt-0.5 size-5" />
      <p>{children}</p>
    </div>
  );
}

/** Aviso referencial canónico (FE-004): siempre texto del loader i18n. */
export function ReferentialNotice() {
  return (
    <p role="note" className="flex items-start gap-2 rounded-xl border border-border-strong bg-canvas p-3 text-ink-muted">
      <Icon name="info" className="mt-0.5 size-5" />
      <span>{t('notice.referential')}</span>
    </p>
  );
}
