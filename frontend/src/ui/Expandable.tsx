// Sección expandible: button[aria-expanded][aria-controls] + región con `hidden` (design.md §10.3).
import { useId, useState, type ReactNode } from 'react';
import { Icon } from './icons';

export interface ExpandableProps {
  readonly openLabel: string;
  readonly closeLabel: string;
  readonly children: ReactNode;
}

export function Expandable({ openLabel, closeLabel, children }: ExpandableProps) {
  const [open, setOpen] = useState(false);
  const regionId = useId();
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={regionId}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex min-h-12 items-center gap-2 rounded-xl px-1 font-semibold text-primary"
      >
        <Icon name="chevron-down" className={`size-5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        {open ? closeLabel : openLabel}
      </button>
      <div id={regionId} hidden={!open} className="mt-2 space-y-3">
        {children}
      </div>
    </div>
  );
}
