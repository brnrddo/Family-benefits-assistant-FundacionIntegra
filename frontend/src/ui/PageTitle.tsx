// h1 único por vista (V-03): fija document.title y recibe el foco al montar (design.md §9, §13).
import { useEffect, useRef } from 'react';
import { t } from '../i18n/copy';

export function PageTitle({ children }: { readonly children: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = `${children} · ${t('app.name')}`;
    ref.current?.focus();
  }, [children]);
  return (
    <h1 ref={ref} tabIndex={-1} className="c3-text focus:outline-none">
      {children}
    </h1>
  );
}
