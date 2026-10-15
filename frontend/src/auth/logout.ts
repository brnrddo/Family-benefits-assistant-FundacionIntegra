// Logout local (FE-007, design.md §12.5 simplificado): aborta requests y vaciado en curso, borra la
// memoria de Query, el snapshot y TODO lo persistido en el dispositivo (caché y cola Demo) y recarga
// la app limpia. Con Cognito, además suelta el usuario y navega al logout del proveedor.
// El diálogo que lo llama avisa antes si hay conversaciones sin enviar.
import type { QueryClient } from '@tanstack/react-query';
import { snapshotStore } from '../api/snapshot';
import { clearQueueSummary } from '../offline/conversationQueue';
import { clearDemoData } from '../offline/db';
import { toastStore } from '../ui/toastStore';
import { getSession } from './session';

export async function performLogout(queryClient: QueryClient, navigate: (url: string) => void = (url) => window.location.assign(url)): Promise<void> {
  const session = getSession();
  session.abortSignal();
  await queryClient.cancelQueries();
  queryClient.clear();
  snapshotStore.reset();
  toastStore.clear();
  await clearDemoData();
  clearQueueSummary();
  if (session.authMode === 'cognito') {
    const logoutUrl = session.logoutUrl();
    await session.removeUser();
    navigate(logoutUrl ?? '/');
    return;
  }
  navigate('/');
}
