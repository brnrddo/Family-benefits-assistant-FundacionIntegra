// Store mínimo de avisos breves (copiado, snapshot cambiado, versión nueva). Textos ya resueltos con t().
import { useSyncExternalStore } from 'react';

export interface ToastAction {
  readonly label: string;
  readonly run: () => void;
}

export interface Toast {
  readonly id: number;
  readonly message: string;
  readonly action?: ToastAction;
}

const AUTO_DISMISS_MS = 5000;
let toasts: readonly Toast[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

function emit(next: readonly Toast[]): void {
  toasts = next;
  for (const listener of [...listeners]) listener();
}

export const toastStore = {
  push(message: string, action?: ToastAction): number {
    const id = nextId++;
    emit([...toasts, { id, message, ...(action ? { action } : {}) }]);
    if (action === undefined) setTimeout(() => toastStore.dismiss(id), AUTO_DISMISS_MS);
    return id;
  },
  dismiss(id: number): void {
    emit(toasts.filter((toast) => toast.id !== id));
  },
  clear(): void {
    emit([]);
  },
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  getSnapshot: (): readonly Toast[] => toasts,
};

export function useToasts(): readonly Toast[] {
  return useSyncExternalStore(toastStore.subscribe, toastStore.getSnapshot, toastStore.getSnapshot);
}
