// Setup global de Vitest (jsdom): jest-dom, IndexedDB falso, polyfill de <dialog> y MSW con
// falla ante requests sin handler (NIT 12). msw 3 renombró onUnhandledRequest → onUnhandledFrame.
import '@testing-library/jest-dom/vitest';
import 'fake-indexeddb/auto';
import { cleanup, configure } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { mockServer, server } from './mswServer';

// La suite completa corre en paralelo (un worker por archivo) y en equipos lentos las vistas con
// varias queries pasan de 1 s: margen para findBy*/waitFor sin cambiar lo que se prueba.
configure({ asyncUtilTimeout: 5000 });

if (typeof HTMLDialogElement !== 'undefined') {
  const proto = HTMLDialogElement.prototype as HTMLDialogElement & { showModal?: () => void; close?: () => void };
  if (typeof proto.showModal !== 'function') {
    proto.showModal = function showModal(this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
  }
  if (typeof proto.close !== 'function') {
    proto.close = function close(this: HTMLDialogElement) {
      this.removeAttribute('open');
      this.dispatchEvent(new Event('close'));
    };
  }
}

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
  mockServer.reset();
  mockServer.setScenario('default');
});

afterAll(() => server.close());
