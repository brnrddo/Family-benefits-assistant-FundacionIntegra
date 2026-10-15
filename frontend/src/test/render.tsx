// Render de pruebas con QueryClient aislado (sin reintentos) y router en memoria.
// FEAT-002/003 pueden extenderlo con el queryClient real y el AppShell.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router';

export interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  readonly route?: string;
  readonly queryClient?: QueryClient;
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const { route = '/', queryClient = createTestQueryClient(), ...rest } = options;
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { ...render(ui, { wrapper, ...rest }), queryClient };
}
