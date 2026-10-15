import { t } from '../../i18n/copy';
import { ButtonLink } from '../../ui/Button';
import { PageTitle } from '../../ui/PageTitle';
import { EmptyState } from '../../ui/states';

export default function NotFoundPage() {
  return (
    <section className="space-y-4">
      <PageTitle>{t('notfound.title')}</PageTitle>
      <EmptyState
        message={t('error.not_found')}
        action={
          <ButtonLink to="/" icon="home" data-primary-action>
            {t('notfound.back_home')}
          </ButtonLink>
        }
      />
    </section>
  );
}
