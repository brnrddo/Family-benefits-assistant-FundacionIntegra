// Pantalla bloqueante de configuración insegura o incompleta (§5.2). Nunca muestra valores ni
// el motivo técnico: solo las claves app.config_error.*. Versión mínima; FEAT-003 la estiliza.
import { t } from '../../i18n/copy';

export function ConfigErrorPage() {
  return (
    <main id="main">
      <h1>{t('app.config_error.title')}</h1>
      <p>{t('app.config_error.body')}</p>
    </main>
  );
}
