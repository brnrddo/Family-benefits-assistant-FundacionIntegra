// Pantalla de bienvenida "Entrar como Tía X (demo)". Solo aparece si la sesión demo aplica
// (`demoSessionEnabled`) y aún no se entró; si no, muestra la app tal cual.
import { useState, type ReactNode } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Icon } from '../../ui/icons';
import { PageTitle } from '../../ui/PageTitle';
import { DEMO_COPY, gateEnter } from './demoCopy';
import { enterDemoSession, useDemoSession } from './session';

export function DemoSessionGate({ children }: { readonly children: ReactNode }) {
  const { seed, active } = useDemoSession();
  const [busy, setBusy] = useState(false);
  if (seed === null || active) return <>{children}</>;
  const enter = async () => {
    setBusy(true);
    try {
      await enterDemoSession();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-5">
      <PageTitle>{DEMO_COPY.gateTitle}</PageTitle>
      <p>{DEMO_COPY.gateIntro}</p>
      <Card className="flex items-center gap-4">
        <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-canvas text-primary">
          <Icon name="user" className="size-8" />
        </span>
        <div className="min-w-0">
          <p className="text-lg font-bold">{seed.tia.display_name}</p>
          <p className="text-ink-muted">
            {DEMO_COPY.gateGardenLabel}: {seed.garden.name}
          </p>
        </div>
      </Card>
      <Button icon="user" data-primary-action className="w-full" busy={busy} onClick={() => void enter()}>
        {gateEnter(seed.tia.display_name)}
      </Button>
    </div>
  );
}
