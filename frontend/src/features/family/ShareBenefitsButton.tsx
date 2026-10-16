// "Compartir beneficios" (SOLO DEMO): simula enviar los beneficios que la familia puede postular ahora.
// No envía ni copia nada: sin API, sin navigator.share, sin portapapeles y sin logs. Al pulsar muestra
// "Beneficios compartidos" unos segundos y el botón queda deshabilitado durante un enfriamiento.
import { useEffect, useRef, useState } from 'react';
import { Button } from '../../ui/Button';
import { FAMILY_COPY } from './familyCopy';

export const SHARE_NOTICE_MS = 3000;
export const SHARE_COOLDOWN_MS = 10000;

export function ShareBenefitsButton() {
  const [noticeVisible, setNoticeVisible] = useState(false);
  const [coolingDown, setCoolingDown] = useState(false);
  const timers = useRef<number[]>([]);

  // Limpia los timers si la ficha se desmonta durante el aviso o el enfriamiento.
  useEffect(
    () => () => {
      timers.current.forEach((id) => window.clearTimeout(id));
    },
    [],
  );

  const share = () => {
    setNoticeVisible(true);
    setCoolingDown(true);
    timers.current = [
      window.setTimeout(() => setNoticeVisible(false), SHARE_NOTICE_MS),
      window.setTimeout(() => setCoolingDown(false), SHARE_COOLDOWN_MS),
    ];
  };

  return (
    <div className="space-y-2">
      <Button variant="secondary" icon="chat" className="w-full" disabled={coolingDown} onClick={share}>
        {FAMILY_COPY.shareButton}
      </Button>
      {/* Región viva siempre montada para que el lector de pantalla anuncie el aviso. */}
      <p role="status" aria-live="polite" className="text-center font-semibold text-go-ink empty:hidden">
        {noticeVisible ? FAMILY_COPY.shareDone : ''}
      </p>
    </div>
  );
}
