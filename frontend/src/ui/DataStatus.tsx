// Procedencia del dato (FE-005, §6.5): caché Demo con antigüedad (banner distinguible) o hora de
// recepción desde la red. C3 no trae fecha del snapshot (PREG-030): nunca se inventa una.
import type { Provider } from '../api/types';
import type { ReadResult } from '../data/queryClient';
import { formatRelative } from '../domain/format';
import { t } from '../i18n/copy';
import { nowMs } from '../lib/now';
import { Chip } from './Chip';
import { Banner } from './states';

export function DataFreshness({ result }: { readonly result: ReadResult<unknown> | undefined }) {
  if (result === undefined) return null;
  if (result.source === 'cache') {
    return (
      <Banner tone="warn" icon="wifi-off">
        {t('data.cached', { when: formatRelative(result.storedAt, nowMs()) })}
      </Banner>
    );
  }
  return <p className="text-[0.9rem] text-ink-muted">{t('data.updated_at', { when: formatRelative(result.receivedAt, nowMs()) })}</p>;
}

/** Insignia de proveedor de redacción y avisos técnicos (sin mostrar los códigos). */
export function ProviderNote({ provider, warnings }: { readonly provider: Provider; readonly warnings: readonly string[] }) {
  return (
    <div className="space-y-2">
      {provider === 'PLANTILLA' ? (
        <>
          <Chip icon="document" tone="neutral" label={t('data.provider.template')} />
          <p className="text-[0.9rem] text-ink-muted">{t('data.provider.template_hint')}</p>
        </>
      ) : (
        <Chip icon="sparkle" tone="other" label={t('data.provider.bedrock')} />
      )}
      {warnings.length > 0 && <p className="text-[0.9rem] text-ink-muted">{t('data.warnings')}</p>}
    </div>
  );
}
