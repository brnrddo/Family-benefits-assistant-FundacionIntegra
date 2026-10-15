// Chip informativo (V-08): ícono + texto obligatorios; el tono nunca es la única señal.
import type { Tone } from '../domain/presentation';
import { Icon, type UiIconName } from './icons';

const TONE: Readonly<Record<Tone, { box: string; icon: string }>> = {
  go: { box: 'bg-go-bg text-go-ink border-go-icon', icon: 'text-go-icon' },
  ask: { box: 'bg-ask-bg text-ask-ink border-ask-icon', icon: 'text-ask-icon' },
  has: { box: 'bg-has-bg text-has-ink border-has-icon', icon: 'text-has-icon' },
  other: { box: 'bg-other-bg text-other-ink border-other-icon', icon: 'text-other-icon' },
  neutral: { box: 'bg-neutral-bg text-ink-muted border-border-strong', icon: 'text-ink-muted' },
};

export interface ChipProps {
  readonly icon: UiIconName;
  readonly label: string;
  readonly tone?: Tone;
}

export function Chip({ icon, label, tone = 'neutral' }: ChipProps) {
  const style = TONE[tone];
  return (
    <span
      className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 py-0.5 text-[0.9rem] font-semibold ${style.box}`}
    >
      <Icon name={icon} className={`size-5 ${style.icon}`} />
      <span>{label}</span>
    </span>
  );
}
