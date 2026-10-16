// Pestañas de la barra inferior: "Mi jardín" y "Preguntar" (plan de arreglos de la demo, decisión 7).
// Las estadísticas del jardín viven en Inicio; la ruta /avance sigue existiendo fuera del menú.
import type { Capabilities } from '../../config/profile';
import type { PlainCopyKey } from '../../i18n/copy';
import type { UiIconName } from '../../ui/icons';
export interface NavItem {
  readonly to: string;
  readonly labelKey: PlainCopyKey;
  readonly icon: UiIconName;
  /** Propaga `?jardin` actual (Inicio). */
  readonly keepGarden: boolean;
  readonly visible?: (capabilities: Capabilities) => boolean;
}
export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', labelKey: 'nav.home', icon: 'home', keepGarden: true },
  { to: '/preguntar', labelKey: 'nav.assistant', icon: 'chat', keepGarden: false },
];
