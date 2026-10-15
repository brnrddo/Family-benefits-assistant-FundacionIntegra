// Tarjeta base: superficie blanca, borde decorativo y sombra suave (design.md §10.2).
import type { HTMLAttributes, ReactNode } from 'react';

export const CARD_CLASS = 'rounded-card border border-border bg-surface p-5 shadow-sm';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  readonly children: ReactNode;
}

export function Card({ className = '', children, ...rest }: CardProps) {
  return (
    <div {...rest} className={`${CARD_CLASS} ${className}`.trim()}>
      {children}
    </div>
  );
}
