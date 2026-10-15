// Región viva de avisos breves (role=status, aria-live=polite).
import { t } from '../i18n/copy';
import { Button } from './Button';
import { toastStore, useToasts } from './toastStore';

export function Toaster() {
  const toasts = useToasts();
  return (
    <div role="status" aria-live="polite" data-print-hide className="pointer-events-none fixed inset-x-0 bottom-24 z-30 mx-auto flex max-w-2xl flex-col gap-2 px-4">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto flex items-center justify-between gap-3 rounded-xl bg-ink px-4 py-3 text-surface shadow-lg">
          <span>{toast.message}</span>
          {toast.action !== undefined ? (
            <Button
              variant="secondary"
              onClick={() => {
                toast.action?.run();
                toastStore.dismiss(toast.id);
              }}
            >
              {toast.action.label}
            </Button>
          ) : (
            <button type="button" className="min-h-11 min-w-11 font-semibold underline" onClick={() => toastStore.dismiss(toast.id)}>
              {t('common.close')}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
