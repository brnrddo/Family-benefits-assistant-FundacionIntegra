// Arranque de la capa de datos (FE-006/FE-007): snapshot persistente Demo, limpieza si el perfil
// no permite persistencia, vaciado de la cola al volver la red / iniciar sesión y revalidación
// de las queries servidas desde caché. Sin sondeo: solo eventos discretos.
import type { QueryClient } from '@tanstack/react-query';
import { snapshotStore } from '../api/snapshot';
import { getSession } from '../auth/session';
import { t } from '../i18n/copy';
import { drain, refreshQueue } from '../offline/conversationQueue';
import { clearDemoData, persistenceEnabled } from '../offline/db';
import { demoSnapshotPersistence } from '../offline/demoCache';
import { refreshLocalNames } from '../offline/localNames';
import { isOnline } from '../offline/network';
import { toastStore } from '../ui/toastStore';
import { invalidateAfterConversation, invalidateCachedQueries } from './queryClient';

export async function initSnapshotStore(queryClient: QueryClient): Promise<void> {
  await snapshotStore.init({
    persistence: persistenceEnabled() ? demoSnapshotPersistence : null,
    effects: {
      invalidateAll: () => void queryClient.invalidateQueries(),
      notifyChanged: () => toastStore.push(t('data.snapshot_changed')),
    },
  });
}

export async function drainAndRefresh(queryClient: QueryClient, manual = false): Promise<number> {
  const { confirmed } = await drain({ manual });
  if (confirmed > 0) await invalidateAfterConversation(queryClient);
  return confirmed;
}

export async function startDataSync(queryClient: QueryClient): Promise<void> {
  // Escala (o sin clasificación sintética): nada persiste; se borra cualquier resto previo.
  if (!persistenceEnabled()) void clearDemoData();
  await initSnapshotStore(queryClient);
  await refreshQueue();
  await refreshLocalNames();

  const resync = () => {
    void invalidateCachedQueries(queryClient);
    void drainAndRefresh(queryClient);
  };
  window.addEventListener('online', resync);

  const session = getSession();
  let previous = session.getState().status;
  session.subscribe(() => {
    const current = session.getState().status;
    if (current === 'authenticated' && previous !== 'authenticated') resync();
    previous = current;
  });

  if (isOnline()) void drainAndRefresh(queryClient);
}
