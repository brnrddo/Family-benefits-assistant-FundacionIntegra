// Detalle técnico (design.md §9.2): U/B/V, puntaje y posición TAL COMO vienen de C3, más la traza
// del BenefitResult del mismo beneficio. Único lugar donde se ven códigos técnicos ([data-technical]).
import type { BenefitResult, Opportunity } from '../../api/types';
import { formatInteger, formatScore } from '../../domain/format';
import { LEVEL_KEY, RESULT_KEY, TRACE_RESULT_KEY } from '../../domain/presentation';
import { t } from '../../i18n/copy';

function ScoreRow({ label, value }: { readonly label: string; readonly value: number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt>{label}</dt>
      <dd className="flex items-center gap-2 font-semibold">
        <meter className="meter" min={0} max={1} value={value} aria-hidden="true" />
        {formatScore(value)}
      </dd>
    </div>
  );
}

export function TechnicalDetail({ opportunity, result }: { readonly opportunity: Opportunity; readonly result: BenefitResult | undefined }) {
  return (
    <div data-technical className="space-y-3 rounded-xl border border-border-strong bg-canvas p-4 text-[0.9rem]">
      <h4 className="font-bold">{t('tech.title')}</h4>
      <dl className="space-y-1">
        <ScoreRow label={t('tech.urgency')} value={opportunity.urgency} />
        <ScoreRow label={t('tech.benefit')} value={opportunity.benefit} />
        <ScoreRow label={t('tech.vulnerability')} value={opportunity.vulnerability} />
        <div className="flex justify-between gap-3">
          <dt>{t('tech.score')}</dt>
          <dd className="font-semibold">{formatScore(opportunity.score)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>{t('tech.position')}</dt>
          <dd className="font-semibold">{formatInteger(opportunity.position)}</dd>
        </div>
      </dl>
      {opportunity.benefit_estimated && <p>{t('tech.benefit_estimated')}</p>}
      {result === undefined ? (
        <p>{t('tech.no_trace')}</p>
      ) : (
        <>
          <dl className="space-y-1">
            <div className="flex justify-between gap-3">
              <dt>{t('tech.result')}</dt>
              <dd>{t(RESULT_KEY[result.result])}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>{t('tech.level')}</dt>
              <dd>{result.level === null ? t('common.not_available') : t(LEVEL_KEY[result.level])}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>{t('tech.access_state')}</dt>
              <dd className="c3-text">{result.access_state}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>{t('tech.missing_codes')}</dt>
              <dd className="c3-text">{result.missing_codes.length === 0 ? t('common.not_available') : result.missing_codes.join(', ')}</dd>
            </div>
          </dl>
          {result.trace.length === 0 ? (
            <p>{t('tech.no_trace')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <caption className="mb-1 text-left font-semibold">{t('tech.trace_title')}</caption>
                <thead>
                  <tr>
                    <th scope="col" className="border-b border-border pr-2">{t('tech.trace.rule')}</th>
                    <th scope="col" className="border-b border-border pr-2">{t('tech.trace.field')}</th>
                    <th scope="col" className="border-b border-border pr-2">{t('tech.trace.operator')}</th>
                    <th scope="col" className="border-b border-border">{t('tech.trace.result')}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trace.map((row, index) => (
                    <tr key={`${row.rule_id}-${index}`}>
                      <td className="c3-text pr-2">{row.rule_id}</td>
                      <td className="c3-text pr-2">{row.field}</td>
                      <td className="c3-text pr-2">{row.operator}</td>
                      <td>{t(TRACE_RESULT_KEY[row.result])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
