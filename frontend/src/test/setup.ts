// Setup global de Vitest (jsdom): jest-dom, IndexedDB falso, polyfill de <dialog> y MSW con
// falla ante requests sin handler (NIT 12). msw 3 renombró onUnhandledRequest → onUnhandledFrame.
import '@testing-library/jest-dom/vitest';
import 'fake-indexeddb/auto';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { mockServer, server } from './mswServer';

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
