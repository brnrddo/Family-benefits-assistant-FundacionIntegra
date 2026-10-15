// Error de render/carga de ruta (design.md §9): nunca muestra error.message, stack ni status.
import { t } from '../../i18n/copy';
import { log } from '../../lib/log';
import { Button, buttonClass } from '../../ui/Button';
import { ErrorState } from '../../ui/states';

export default function RouteErrorPage() {
  log.error({ kind: 'render' });
  return (
    <main id="main" className="mx-auto max-w-2xl space-y-4 p-4">
      <h1>{t('error.generic.title')}</h1>
      <ErrorState
        error={null}
        action={
          <>
            <Button variant="secondary" icon="refresh" onClick={() => window.location.reload()}>
              {t('common.retry')}
            </Button>
            <a href="/" className={buttonClass('ghost')}>
              {t('notfound.back_home')}
            </a>
          </>
        }
      />
    </main>
  );
}
