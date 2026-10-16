// h1 único por vista (V-03): fija document.title y recibe el foco al montar (design.md §9, §13).
import { useEffect, useRef } from 'react';
import { APP_NAME } from '../brand';

/**
 * `documentTitle` reemplaza el texto en `document.title` (historial del navegador): la ficha lo usa
 * para que un nombre de trato local nunca quede en el historial, que el logout no borra (DEC-038).
 */
export function PageTitle({ children, documentTitle }: { readonly children: string; readonly documentTitle?: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  const tabTitle = documentTitle ?? children;
  useEffect(() => {
    document.title = `${tabTitle} · ${APP_NAME}`;
    ref.current?.focus();
  }, [children, tabTitle]);
  return (
    <h1 ref={ref} tabIndex={-1} className="c3-text focus:outline-none">
      {children}
    </h1>
  );
}
