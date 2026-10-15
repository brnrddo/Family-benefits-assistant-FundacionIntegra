// Botones y enlaces con forma de botón (V-09: ≥ 48 px de alto; V-10: busy inmediato).
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router';
import { Icon, type UiIconName } from './icons';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';

const BASE =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl py-2 text-center font-semibold transition duration-100 active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-70';

const VARIANT: Readonly<Record<ButtonVariant, string>> = {
  primary: 'bg-primary text-surface hover:bg-primary-strong active:bg-primary-strong',
  secondary: 'border-2 border-primary bg-surface text-primary hover:bg-canvas',
  ghost: 'text-primary underline-offset-4 hover:underline',
};

export type ButtonSize = 'md' | 'sm';

const SIZE: Readonly<Record<ButtonSize, string>> = { md: 'px-5', sm: 'px-2' };

export function buttonClass(variant: ButtonVariant = 'primary', extra = '', size: ButtonSize = 'md'): string {
  return `${BASE} ${SIZE[size]} ${VARIANT[variant]} ${extra}`.trim();
}

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  readonly variant?: ButtonVariant;
  readonly icon?: UiIconName;
  readonly busy?: boolean;
  readonly size?: ButtonSize;
  readonly children: ReactNode;
}

export function Button({ variant = 'primary', icon, busy = false, size = 'md', disabled, className = '', children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled === true || busy}
      aria-busy={busy || undefined}
      className={buttonClass(variant, className, size)}
    >
      {icon !== undefined && <Icon name={busy ? 'refresh' : icon} className={busy ? 'size-5 animate-spin' : 'size-5'} />}
      {children}
    </button>
  );
}

export interface ButtonLinkProps extends Omit<LinkProps, 'className' | 'children'> {
  readonly variant?: ButtonVariant;
  readonly icon?: UiIconName;
  readonly className?: string;
  readonly children: ReactNode;
}

export function ButtonLink({ variant = 'primary', icon, className = '', children, ...rest }: ButtonLinkProps) {
  return (
    <Link {...rest} className={buttonClass(variant, className)}>
      {icon !== undefined && <Icon name={icon} className="size-5" />}
      {children}
    </Link>
  );
}
