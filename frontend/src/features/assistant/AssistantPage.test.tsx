// Asistente de catálogo con el mock-servidor C3. Preguntas inventadas; datos 100 % sintéticos
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { AssistantEnvelope } from '../../api/types';
import { t } from '../../i18n/copy';
import { payloadOf } from '../../test/fixtures';
import { mockServer, server } from '../../test/mswServer';
import { overrideOperation } from '../../test/operations';
import { renderWithProviders } from '../../test/render';
import { installTestRuntime, resetTestRuntime } from '../../test/runtime';
import AssistantPage from './AssistantPage';

function renderAssistant() {
  return renderWithProviders(<AssistantPage />, { route: '/preguntar' });
}

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole('textbox', { name: new RegExp(t('assistant.question_label')) }), question);
  await user.click(screen.getByRole('button', { name: t('assistant.submit') }));
}

describe('AssistantPage', () => {
  beforeEach(() => installTestRuntime());
  afterEach(() => resetTestRuntime());

  it('CATALOG_INFO → respuesta como texto, citas HTTPS tipadas y aviso', async () => {
    renderAssistant();
    expect(screen.getByRole('button', { name: t('assistant.submit') })).toBeDisabled();
    await ask('¿Qué apoyos existen para niños en jardín infantil?');
    const envelope = payloadOf<AssistantEnvelope>('askCatalogAssistant.catalog-info');
    const answer = await screen.findByText((_, el) => el?.textContent === envelope.answer && el.classList.contains('c3-text'));
    expect(answer).toHaveClass('whitespace-pre-line');
    // Los únicos enlaces son las citas de C3 (SourceLink, HTTPS).
    const links = screen.getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual(envelope.citations.map((c) => c.url));
    for (const link of links) expect(link).toHaveAttribute('rel', 'noopener noreferrer external');
    expect(screen.getByText(t('notice.referential'))).toBeInTheDocument();
  });

  it('REQUIRES_DETERMINISTIC_EVALUATION → deriva a Mi jardín sin mostrar la respuesta', async () => {
    mockServer.setScenario('assistantDeterministic');
    renderAssistant();
    await ask('¿Esta familia recibe el aporte?');
    expect(await screen.findByText(t('assistant.deterministic_redirect'))).toBeInTheDocument();
    expect(screen.getByRole('link', { name: t('assistant.go_home') })).toHaveAttribute('href', '/');
    expect(document.body.textContent).not.toContain(payloadOf<AssistantEnvelope>('askCatalogAssistant.deterministic').answer);
  });

  it('RUT, teléfono o correo → bloqueado sin enviar', async () => {
    let calls = 0;
    server.use(
      overrideOperation('askCatalogAssistant', () => {
        calls += 1;
        return HttpResponse.json(payloadOf('askCatalogAssistant.catalog-info'), { status: 200 });
      }),
    );
    renderAssistant();
    await ask('¿Qué recibe el RUT 12.345.678-5?');
    expect(await screen.findByRole('alert')).toHaveTextContent(t('assistant.pii_blocked'));
    expect(calls).toBe(0);
  });

  it('la API falla → plantilla fija en español con Reintentar, sin texto del servidor', async () => {
    server.use(overrideOperation('askCatalogAssistant', () => HttpResponse.json(payloadOf('error.503'), { status: 503 })));
    renderAssistant();
    await ask('¿Dónde se actualiza el Registro Social de Hogares?');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(t('error.unavailable'));
    const card = alert.closest('div') as HTMLElement;
    expect(within(card).getByText(t('data.provider.template'))).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: t('common.retry') })).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('Dependencia sin fallback seguro');
  });
});
