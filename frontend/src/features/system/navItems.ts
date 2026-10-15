// Pestañas de la barra inferior (design.md §9): 4 en local/demo, 3 en `escala` (sin Familia nueva).
import type { Capabilities } from '../../config/profile';
import type { PlainCopyKey } from '../../i18n/copy';
import type { UiIconName } from '../../ui/icons';

export interface NavItem {
  readonly to: string;
  readonly labelKey: PlainCopyKey;
  readonly icon: UiIconName;
  /** Propaga `?jardin` actual (Inicio, Familia nueva y Avance). */
  readonly keepGarden: boolean;
  readonly visible?: (capabilities: Capabilities) => boolean;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', labelKey: 'nav.home', icon: 'home', keepGarden: true },
  { to: '/familia-nueva', labelKey: 'nav.new_family', icon: 'user-plus', keepGarden: true, visible: (c) => c.newFamily },
  { to: '/avance', labelKey: 'nav.kpi', icon: 'chart', keepGarden: true },
  { to: '/preguntar', labelKey: 'nav.assistant', icon: 'chat', keepGarden: false },
];
