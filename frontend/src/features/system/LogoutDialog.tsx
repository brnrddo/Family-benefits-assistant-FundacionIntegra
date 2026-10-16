// Confirmación de logout con <dialog> nativo (FE-007): avisa si hay conversaciones sin enviar o
// nombres de trato guardados (DEC-038) antes de borrarlos del dispositivo. Cancelar no borra nada.
import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { performLogout } from '../../auth/logout';
import { formatInteger } from '../../domain/format';
import { t } from '../../i18n/copy';
import { useQueueSummary } from '../../offline/conversationQueue';
import { useLocalNames } from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { clearDemoSession } from '../demo-session/session';

export function LogoutButton() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const queryClient = useQueryClient();
  const queue = useQueueSummary();
  const names = useLocalNames();
  const [busy, setBusy] = useState(false);
  const pending = queue.entries.length;

  const confirm = async () => {
    setBusy(true);
    try {
      clearDemoSession();
      await performLogout(queryClient);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {/* A 360 px solo el ícono (nombre accesible en sr-only) para no cortar el nombre de la app. */}
      <Button variant="ghost" size="sm" icon="logout" className="min-w-12 shrink-0" onClick={() => dialogRef.current?.showModal()}>
        <span className="sr-only min-[400px]:not-sr-only">{t('auth.logout')}</span>
      </Button>
      <dialog ref={dialogRef} aria-labelledby="logout-title" className="m-auto max-w-sm rounded-card bg-surface p-6 text-ink shadow-xl backdrop:bg-ink/40">
        <h2 id="logout-title">{t('auth.logout_confirm.title')}</h2>
        <p className="mt-2">
          {pending > 0 ? t('auth.logout_confirm.body_pending', { count: formatInteger(pending) }) : t('auth.logout_confirm.body')}
        </p>
        {names.size > 0 && <p className="mt-2 font-semibold">{t('auth.logout_confirm.body_names', { count: formatInteger(names.size) })}</p>}
        <div className="mt-4 flex flex-col gap-2">
          <Button busy={busy} icon="logout" onClick={() => void confirm()}>
            {t('auth.logout_confirm.accept')}
          </Button>
          <Button variant="secondary" disabled={busy} onClick={() => dialogRef.current?.close()}>
            {t('auth.logout_confirm.cancel')}
          </Button>
        </div>
      </dialog>
    </>
  );
}
