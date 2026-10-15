// Raíz de la app: QueryClient + router. Las vistas consumen C3 solo vía data/queries y data/mutations.
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { RouterProvider } from 'react-router';
import { createAppRouter } from './router';

export default function App({ queryClient }: { readonly queryClient: QueryClient }) {
  const [router] = useState(createAppRouter);
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
