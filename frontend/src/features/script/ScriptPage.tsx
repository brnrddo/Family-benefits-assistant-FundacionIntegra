// Guion (design.md §9.3): se genera con los top_opportunities de la ficha en el orden de C3.
// El texto del modelo/plantilla se muestra solo como texto (pre-line, aislado bidi).
import { useParams } from 'react-router';
import { useFamilia, useGuion } from '../../data/queries';
import { isValidId } from '../../domain/ids';
import { t } from '../../i18n/copy';
import { ButtonLink } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ProviderNote } from '../../ui/DataStatus';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState, ErrorState, ReferentialNotice, Skeleton } from '../../ui/states';
import { familyRoutes } from '../family/routes';
import NotFoundPage from '../system/NotFoundPage';

function ScriptView({ familyId }: { readonly familyId: string }) {
  const ficha = useFamilia(familyId);
  const benefitIds = ficha.data?.body.data.top_opportunities.map((o) => o.benefit_id) ?? [];
  const guion = useGuion(familyId, benefitIds);

  let body;
  if (ficha.isPending || (benefitIds.length > 0 && guion.isPending)) {
    body = (
      <>
        <p className="text-ink-muted">{t('script.generating')}</p>
        <Skeleton rows={1} rowClass="h-48" />
      </>
    );
  } else if (ficha.isError && ficha.data === undefined) {
    body = <ErrorState error={ficha.error} onRetry={() => void ficha.refetch()} />;
  } else if (benefitIds.length === 0) {
    body = <EmptyState message={t('empty.opportunities')} />;
  } else if (guion.isError) {
    body = <ErrorState error={guion.error} onRetry={() => void guion.refetch()} />;
  } else if (guion.data !== undefined) {
    const envelope = guion.data.body;
    body = (
      <>
        <ProviderNote provider={envelope.provider} warnings={envelope.warnings} />
        <Card>
          <p className="c3-text whitespace-pre-line text-lg leading-relaxed">{envelope.content.script}</p>
        </Card>
        <p className="text-ink-muted">{t('script.read_hint')}</p>
        <ReferentialNotice />
        <ButtonLink to={familyRoutes.conversacion(familyId)} icon="check" data-primary-action className="w-full">
          {t('family.actions.mark')}
        </ButtonLink>
      </>
    );
  }

  return (
    <div className="space-y-4">
      <ButtonLink to={familyRoutes.ficha(familyId)} variant="ghost" icon="chevron-left" className="-ml-3">
        {t('nav.back')}
      </ButtonLink>
      <PageTitle>{t('script.title')}</PageTitle>
      {body}
    </div>
  );
}

export default function ScriptPage() {
  const { familyId } = useParams();
  if (!isValidId(familyId)) return <NotFoundPage />;
  return <ScriptView key={familyId} familyId={familyId} />;
}
