// Shell (design.md §9): salto al contenido, cabecera, banners sintético/offline, <main>,
// pie con snapshot y barra inferior. Las vistas se cargan diferidas dentro de RequireSession.
import { Suspense } from 'react';
import { NavLink, Outlet, useMatch, useSearchParams } from 'react-router';
import { copySource } from 'virtual:brujula-content';
import { useSnapshotState } from '../../api/snapshot';
import { RequireSession } from '../../auth/RequireSession';
import { APP_NAME } from '../../brand';
import { runtimeConfig } from '../../config/profile';
import { t } from '../../i18n/copy';
import { useOnline } from '../../offline/network';
import { Icon } from '../../ui/icons';
import { Banner, Skeleton } from '../../ui/states';
import { Toaster } from '../../ui/Toaster';
import { headerLabel } from '../demo-session/demoCopy';
import { DemoSessionGate } from '../demo-session/DemoSessionGate';
import { useDemoSession } from '../demo-session/session';
import { LogoutButton } from './LogoutDialog';
import { NAV_ITEMS } from './navItems';

function BottomNav() {
  const { capabilities } = runtimeConfig();
  const [search] = useSearchParams();
  const garden = search.get('jardin');
  const items = NAV_ITEMS.filter((item) => item.visible?.(capabilities) ?? true);
  return (
    // Móvil: barra fija abajo. Escritorio (≥1024 px): barra superior bajo la cabecera, en el flujo.
    <nav
      aria-label={t('nav.main_label')}
      data-print-hide
      className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface lg:static lg:border-b lg:border-t-0"
    >
      <ul className="mx-auto flex max-w-2xl justify-around lg:max-w-6xl lg:justify-start lg:gap-2 lg:px-4">
        {items.map((item) => {
          const to = item.keepGarden && garden !== null ? `${item.to}?${new URLSearchParams({ jardin: garden }).toString()}` : item.to;
          return (
            <li key={item.to} className="flex-1 lg:flex-none">
              <NavLink
                to={to}
                end
                className={({ isActive }) =>
                  // Altura fija (h-18): las CTA fijas de Ficha/Conversación usan `bottom-18` para quedar encima.
                  `flex h-18 flex-col items-center justify-start gap-0.5 px-1 pt-2 text-center text-[0.85rem] font-semibold leading-tight lg:h-12 lg:flex-row lg:justify-center lg:gap-2 lg:rounded-xl lg:px-4 lg:pt-0 lg:text-base ${isActive ? 'text-primary lg:bg-canvas' : 'text-ink-muted'}`
                }
              >
                <Icon name={item.icon} className="size-5" />
                {t(item.labelKey)}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default function AppShell() {
  const { capabilities } = runtimeConfig();
  const online = useOnline();
  const snapshot = useSnapshotState();
  const demo = useDemoSession();
  // Escritorio: Inicio usa el ancho útil (2 columnas); las vistas de una columna, un ancho legible.
  const wide = useMatch({ path: '/', end: true }) !== null;
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-surface focus:p-3">
        {t('app.skip_to_content')}
      </a>
      <header data-print-hide className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-2 px-4 py-1 lg:max-w-6xl">
          <NavLink to="/" className="flex min-h-12 min-w-0 items-center gap-2 font-bold text-primary">
            <Icon name="compass" className="size-7 shrink-0" />
            <span className="flex min-w-0 flex-col leading-tight">
              <span className="truncate">{APP_NAME}</span>
              {demo.active && demo.seed !== null && (
                <span className="truncate text-[0.85rem] font-semibold text-ink-muted">
                  {headerLabel(demo.seed.tia.display_name, demo.seed.garden.name)}
                </span>
              )}
            </span>
          </NavLink>
          <LogoutButton />
        </div>
      </header>
      <BottomNav />
      <div data-print-hide>
        {copySource !== 'CANONICAL' && (
          <Banner tone="warn" icon="document">
            {t('app.copy_mock_badge')}
          </Banner>
        )}
        {capabilities.syntheticBanner && <Banner tone="info">{t('app.synthetic_banner')}</Banner>}
        {!online && (
          <Banner tone="warn" icon="wifi-off">
            {t('app.offline_banner')}
          </Banner>
        )}
      </div>
      <main
        id="main"
        tabIndex={-1}
        className={`mx-auto w-full max-w-2xl flex-1 px-4 pb-8 pt-4 focus:outline-none lg:pt-6 ${wide ? 'lg:max-w-6xl' : 'lg:max-w-4xl'}`}
      >
        <RequireSession>
          <DemoSessionGate>
            <Suspense fallback={<Skeleton rows={4} />}>
              <Outlet />
            </Suspense>
          </DemoSessionGate>
        </RequireSession>
      </main>
      <footer data-print-hide className="px-4 pb-24 text-center text-[0.9rem] text-ink-muted lg:pb-6">
        {snapshot.active !== null && t('data.snapshot', { snapshot_id: snapshot.active })}
      </footer>
      <Toaster />
    </div>
  );
}
