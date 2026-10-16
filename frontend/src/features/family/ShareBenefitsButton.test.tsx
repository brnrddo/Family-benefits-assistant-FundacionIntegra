// "Compartir beneficios" (solo demo): no envía nada; solo aviso temporal y enfriamiento.
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FAMILY_COPY } from './familyCopy';
import { SHARE_COOLDOWN_MS, SHARE_NOTICE_MS, ShareBenefitsButton } from './ShareBenefitsButton';

describe('ShareBenefitsButton (solo demo)', () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('al pulsar muestra "Beneficios compartidos" y queda deshabilitado', () => {
    render(<ShareBenefitsButton />);
    const button = screen.getByRole('button', { name: FAMILY_COPY.shareButton });
    fireEvent.click(button);
    expect(screen.getByRole('status')).toHaveTextContent(FAMILY_COPY.shareDone);
    expect(button).toBeDisabled();
  });

  it('el aviso se va a los ~3 s y el botón se rehabilita tras el enfriamiento', () => {
    vi.useFakeTimers();
    render(<ShareBenefitsButton />);
    const button = screen.getByRole('button', { name: FAMILY_COPY.shareButton });
    fireEvent.click(button);
    act(() => vi.advanceTimersByTime(SHARE_NOTICE_MS));
    expect(screen.getByRole('status')).not.toHaveTextContent(FAMILY_COPY.shareDone);
    expect(button).toBeDisabled();
    act(() => vi.advanceTimersByTime(SHARE_COOLDOWN_MS - SHARE_NOTICE_MS));
    expect(button).toBeEnabled();
  });
});
