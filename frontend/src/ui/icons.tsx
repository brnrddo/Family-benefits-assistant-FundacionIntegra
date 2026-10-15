// Íconos propios (design.md §10.2, V-17): único lugar con <svg>. Siempre decorativos
// (aria-hidden) y acompañados de texto; los trazos son constantes de este archivo.
import type { IconName } from '../domain/presentation';

export type UiIconName =
  | IconName
  | 'compass'
  | 'home'
  | 'user'
  | 'child'
  | 'chevron-down'
  | 'chevron-left'
  | 'copy'
  | 'print'
  | 'external'
  | 'wifi-off'
  | 'refresh'
  | 'chat'
  | 'logout'
  | 'sparkle'
  | 'document'
  | 'coins'
  | 'chart'
  | 'user-plus';

const circle = (cx: number, cy: number, r: number): string =>
  `M${cx + r} ${cy}a${r} ${r} 0 1 1-${2 * r} 0a${r} ${r} 0 1 1 ${2 * r} 0`;

const PATHS: Readonly<Record<UiIconName, readonly string[]>> = {
  check: ['M5 12.5l4.5 4.5L19 7.5'],
  question: [circle(12, 12, 9), 'M9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.7.4-1.1 1-1.1 1.8v.5', 'M12 17h.01'],
  mailbox: ['M3 7h18v12H3z', 'M3 7l9 7 9-7'],
  clock: [circle(12, 12, 9), 'M12 7v5l3.5 2'],
  info: [circle(12, 12, 9), 'M12 11v6', 'M12 7.5h.01'],
  dash: ['M6 12h12'],
  alert: ['M12 3.5l9.5 16.5h-19z', 'M12 10v4.5', 'M12 17.5h.01'],
  calendar: ['M4 6h16v14H4z', 'M4 10h16', 'M8 3v4', 'M16 3v4'],
  compass: [circle(12, 12, 9), 'M15.5 8.5l-2 5-5 2 2-5z'],
  home: ['M4 10.5L12 4l8 6.5V20H4z', 'M10 20v-5h4v5'],
  user: [circle(12, 8, 4), 'M4.5 20.5a7.5 7.5 0 0 1 15 0'],
  child: [circle(12, 7, 3), 'M7.5 20.5v-3a4.5 4.5 0 0 1 9 0v3'],
  'chevron-down': ['M6 9l6 6 6-6'],
  'chevron-left': ['M15 6l-6 6 6 6'],
  copy: ['M8 8h12v12H8z', 'M16 8V4H4v12h4'],
  print: ['M7 9V3h10v6', 'M7 17H4v-7h16v7h-3', 'M7 14h10v7H7z'],
  external: ['M14 4h6v6', 'M20 4l-9 9', 'M18 14v6H4V6h6'],
  'wifi-off': ['M3 3l18 18', 'M8.5 16.5a5 5 0 0 1 7 0', 'M12 20h.01', 'M4.5 12.5a11 11 0 0 1 4-2.6', 'M19.5 12.5a11 11 0 0 0-3.2-2.2'],
  refresh: ['M20 11a8 8 0 1 0-2.3 5.7', 'M20 4v7h-7'],
  chat: ['M4 5h16v11H9l-5 4z'],
  logout: ['M10 4H5v16h5', 'M16 8l4 4-4 4', 'M20 12H9'],
  sparkle: ['M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z'],
  document: ['M6 3h9l3 3v15H6z', 'M9 11h6', 'M9 15h6'],
  coins: [circle(12, 12, 9), 'M14.5 9h-3.5a1.5 1.5 0 0 0 0 3h2a1.5 1.5 0 0 1 0 3H9.5', 'M12 7.5V9', 'M12 15v1.5'],
  chart: ['M4 20h16', 'M7 16v-5', 'M12 16V7', 'M17 16v-8'],
  'user-plus': [circle(10, 8, 4), 'M3 20.5a7 7 0 0 1 14 0', 'M19 8v6', 'M16 11h6'],
};

export interface IconProps {
  readonly name: UiIconName;
  readonly className?: string;
}

export function Icon({ name, className = 'size-6' }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-icon={name}
      className={`shrink-0 ${className}`}
    >
      {PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
