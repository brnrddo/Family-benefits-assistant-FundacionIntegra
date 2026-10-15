// Todos los beneficios de la ficha en dos grupos claros (cambio 3): "Beneficios que aplica" (SI, con
// estado de acceso y nivel CONFIRMADO/PRELIMINAR) y "Falta información" (INDETERMINADO o pendiente de
// antecedentes, con el dato que falta en lenguaje simple y la pregunta sugerida de C3). Solo
// presentación de lo que entrega C3 (domain/benefitGroups.ts); no infiere elegibilidad (FE-003).
import type { FamilyDetail, MissingCode, Opportunity } from '../../api/types';
import { groupBenefits, type BenefitRow } from '../../domain/benefitGroups';
import { accessPresentation, ACCESS_STATE_KEY, LEVEL_KEY, MISSING_CODE_KEY } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { CARD_CLASS } from '../../ui/Card';
import { Chip } from '../../ui/Chip';
import { EmptyState } from '../../ui/states';

const isMissingCode = (code: string): code is MissingCode => Object.prototype.hasOwnProperty.call(MISSING_CODE_KEY, code);

/** Datos faltantes en lenguaje simple; un código sin traducción se muestra como genérico (sin el código). */
function missingLabels(codes: readonly string[]): string[] {
  return [...new Set(codes.map((code) => (isMissingCode(code) ? t(MISSING_CODE_KEY[code]) : t('family.missing_generic'))))];
}

function RowChips({ row }: { readonly row: BenefitRow }) {
  const group = accessPresentation(row.accessState);
  return (
    <div className="flex flex-wrap gap-2">
      {group !== null && <Chip icon={group.icon} tone={group.tone} label={t(group.labelKey)} />}
      {row.level !== null && (
        <Chip icon={row.level === 'CONFIRMADO' ? 'check' : 'info'} tone={row.level === 'CONFIRMADO' ? 'neutral' : 'other'} label={t(LEVEL_KEY[row.level])} />
      )}
    </div>
  );
}

function AppliesItem({ row }: { readonly row: BenefitRow }) {
  const pending = missingLabels(row.missingCodes);
  return (
    <li className={`${CARD_CLASS} space-y-2`}>
      <h3 className="c3-text">{benefitName(row.benefitId, row.simpleTitle)}</h3>
      <RowChips row={row} />
      <p className="text-ink-muted">{t(ACCESS_STATE_KEY[row.accessState])}</p>
      {pending.length > 0 && (
        <p>
          <span className="font-semibold">{t('family.pending_confirm_label')}</span> {pending.join(' · ')}
        </p>
      )}
    </li>
  );
}

function MissingItem({ row }: { readonly row: BenefitRow }) {
  const missing = missingLabels(row.missingCodes);
  return (
    <li className={`${CARD_CLASS} space-y-2`}>
      <h3 className="c3-text">{benefitName(row.benefitId, row.simpleTitle)}</h3>
      <RowChips row={row} />
      <div>
        <p className="font-semibold">{t('family.missing_data_label')}</p>
        <ul className="list-disc pl-6">
          {(missing.length > 0 ? missing : [t('family.missing_generic')]).map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </div>
      {row.questions.length > 0 && (
        <div>
          <p className="font-semibold">{t('family.suggested_question_label')}</p>
          <ul className="list-disc pl-6">
            {row.questions.map((question) => (
              <li key={question} className="c3-text">
                {question}
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

export function BenefitGroups({ detail, opportunities }: { readonly detail: FamilyDetail; readonly opportunities: readonly Opportunity[] }) {
  const { applies, missing } = groupBenefits(detail, opportunities);
  return (
    <>
      <section aria-labelledby="family-applies" data-benefit-group="applies" className="space-y-3">
        <h2 id="family-applies">{t('family.applies_title')}</h2>
        {applies.length === 0 ? (
          <EmptyState message={t('family.applies_empty')} />
        ) : (
          <ul className="space-y-3">
            {applies.map((row) => (
              <AppliesItem key={row.benefitId} row={row} />
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="family-missing" data-benefit-group="missing" className="space-y-3">
        <h2 id="family-missing">{t('family.missing_title')}</h2>
        {missing.length === 0 ? (
          <EmptyState message={t('family.missing_empty')} />
        ) : (
          <ul className="space-y-3">
            {missing.map((row) => (
              <MissingItem key={row.benefitId} row={row} />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
