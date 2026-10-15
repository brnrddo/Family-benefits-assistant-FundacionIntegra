// Mensaje + tarjeta CARD_V1 con el mock-servidor C3, incluida la prueba adversarial de render seguro
// (design.md §11.4). Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { t } from '../../i18n/copy';
import { mensajeAdversarial, mensajeBedrock } from '../../test/fixtures';
import { mockServer } from '../../test/mswServer';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import MessagePage from './MessagePage';

function renderMessage() {
  return renderWithProviders(
    <Routes>
      <Route path="/familias/:familyId/mensaje" element={<MessagePage />} />
    </Routes>,
    { route: '/familias/FAM-SIM-E3-00001/mensaje' },
  );
}

describe('MessagePage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => {
    vi.restoreAllMocks();
    resetTestRuntime();
  });

  it('vista previa solo para copiar, tarjeta CARD_V1 con aviso e impresión', async () => {
    const user = userEvent.setup();
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    renderMessage();
    const content = mensajeBedrock().content;
    expect(await screen.findByText(content.whatsapp_preview)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: t('message.copy') }));
    expect(await navigator.clipboard.readText()).toBe(content.whatsapp_preview);
    expect(document.querySelector('a[href*="wa.me"]')).toBeNull();

    const card = document.querySelector('[data-print-root]') as HTMLElement;
    expect(within(card).getByRole('heading', { level: 2, name: content.printable_card.title })).toBeInTheDocument();
    expect(within(card).getByText(t('notice.referential'))).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: t('message.print') }));
    expect(print).toHaveBeenCalledOnce();
  });

  it('cita http:// (inválida para C3) → error contractual y no se renderiza la tarjeta', async () => {
    mockServer.setScenario('invalidCitation');
    renderMessage();
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText(t('error.contract'))).toBeInTheDocument();
    expect(document.querySelector('[data-print-root]')).toBeNull();
  });

  it('strings adversariales (<script>, onerror=, javascript:, bidi) quedan como texto inerte', async () => {
    mockServer.setScenario('adversarialCard');
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {});
    renderMessage();
    const envelope = mensajeAdversarial();
    const cardData = envelope.content.printable_card;
    const card = (await screen.findByRole('heading', { level: 2, name: cardData.title })).closest('[data-print-root]') as HTMLElement;
    const root = document.body;

    // Texto literal intacto y dentro de contenedores aislados (.c3-text).
    expect(within(card).getByText(cardData.title)).toHaveClass('c3-text');
    expect(within(card).getByText(cardData.introduction)).toHaveClass('c3-text');
    expect(within(card).getByText('javascript:alert(1)')).toHaveClass('c3-text');
    expect(screen.getByText(envelope.content.whatsapp_preview)).toHaveClass('c3-text');

    // Ningún elemento activo ni markup inyectado.
    expect(root.querySelectorAll('script, img, iframe, style, object, embed, link')).toHaveLength(0);
    for (const svg of root.querySelectorAll('svg')) expect(svg.getAttribute('data-icon')).not.toBeNull();
    for (const el of root.querySelectorAll('*')) {
      for (const attr of el.getAttributeNames()) {
        expect(attr.startsWith('on')).toBe(false);
        expect(attr).not.toBe('style');
      }
    }
    // Únicos enlaces de la tarjeta: citas HTTPS tipadas de C3.
    const allowed = new Set(cardData.sections.flatMap((s) => s.sources.map((src) => new URL(src.url).href)));
    const hrefs = [...card.querySelectorAll('a[href]')].map((a) => a.getAttribute('href') ?? '');
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href.startsWith('https://')).toBe(true);
      expect(allowed.has(href)).toBe(true);
    }
    expect(root.querySelector('a[href^="javascript:"]')).toBeNull();
    // Aviso y rótulos de la plantilla fuera de los contenedores de texto de C3.
    const notice = within(card).getByText(t('notice.referential'));
    expect(notice.closest('.c3-text')).toBeNull();
    expect(alert).not.toHaveBeenCalled();
  });
});
