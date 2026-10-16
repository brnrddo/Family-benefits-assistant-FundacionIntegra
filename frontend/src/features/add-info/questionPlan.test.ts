// Selección determinista de preguntas (DEC-093). Ficha 100 % sintética inline
// (data_classification: SYNTHETIC_DEMO_NOT_A_REAL_PERSON); IDs y títulos inventados.
import { describe, expect, it } from 'vitest';
import { ADD_INFO_COPY } from '../../api/proposals/addInfoCopy';
import type { BenefitResult, FamilyDetail, Opportunity } from '../../api/types';
import { yearsLabel } from '../../i18n/copy';
import { MAX_PRIMARY_QUESTIONS, planQuestions } from './questionPlan';

const DEMO_TITLE = 'Bono de prueba (programa de demostración)';

function result(benefit_id: string, kind: 'IND' | 'PEND', missing_codes: string[]): BenefitResult {
  return kind === 'IND'
    ? { benefit_id, result: 'INDETERMINADO', level: null, access_state: 'INDETERMINADO', missing_codes, trace: [] }
    : { benefit_id, result: 'SI', level: 'PRELIMINAR', access_state: 'PENDIENTE_ANTECEDENTES', missing_codes, trace: [] };
}

function opportunity(row: BenefitResult, simple_title: string, position: number): Opportunity {
  return {
    benefit_id: row.benefit_id,
    simple_title,
    result: row.result,
    level: row.level,
    access_state: row.access_state,
    urgency: 0.5,
    benefit: 0.5,
    vulnerability: 0.5,
    score: 1,
    position,
    estimated_annual_amount: null,
    benefit_estimated: false,
    action_type: 'ASK_FIRST',
    why_first: 'Falta un dato.',
    missing_codes: row.missing_codes,
    suggested_questions: [],
    where_to_go: null,
    sources: [{ source_id: 'SRC-SIM-1', title: 'Fuente sintética', url: null }],
  } as unknown as Opportunity;
}

describe('planQuestions', () => {
  it('limita, ordena por impacto (empate: posición del motor) y etiqueta con nombres legibles', () => {
    const maternal = result('BEN-SIM-901', 'IND', ['semanas_gestacion', 'cobertura_incompatible']);
    const demo = result('BEN-SIM-902', 'IND', ['semanas_gestacion', 'tramo_rsh']);
    const noTitle = result('BEN-SIM-903', 'IND', ['income_band']);
    const control = result('BEN-SIM-904', 'IND', ['last_health_control_date']);
    const pending = result('BEN-SIM-905', 'PEND', ['housing_type']);
    const detail = {
      family_id: 'FAM-SIM-E3-90001',
      garden_id: 'JAR-SIM-E3-90001',
      composition: [
        { role: 'ADULT_REFERENCE', age: 30 },
        { role: 'CHILD', age: 4 },
        { role: 'CHILD', age: 1 },
      ],
      rsh_band: 40,
      informed: false,
      top_opportunities: [],
      benefit_results: [maternal, demo, noTitle, control, pending],
      disclaimer: 'Orientación referencial; no determina derechos. Confirmar en la institución.',
    } as FamilyDetail;
    const prioridad = [
      opportunity(maternal, 'Subsidio Maternal', 1),
      opportunity(demo, DEMO_TITLE, 2),
      opportunity(control, 'Control de salud infantil', 3),
      opportunity(pending, 'Apoyo de vivienda', 4),
    ];

    const plan = planQuestions({ detail, opportunities: prioridad, declared: new Set() });

    expect(plan.primary).toHaveLength(MAX_PRIMARY_QUESTIONS);
    // Embarazo destraba 2 INDETERMINADO; el resto 1 (empate por posición); vivienda solo completa un SI pendiente.
    expect([...plan.primary, ...plan.more].map((q) => q.key)).toEqual([
      'household_pregnancy',
      'has_incompatible_coverage',
      'rsh_band',
      'last_child_health_control_date',
      'household_income_band',
      'housing_type',
    ]);
    expect(plan.primary[0]?.dependents).toEqual(['pregnancy_weeks_at_least_threshold']);
    expect(plan.primary[0]?.opens).toEqual(['Subsidio Maternal', DEMO_TITLE]);
    expect(plan.more.find((q) => q.key === 'household_income_band')?.opens).toEqual([ADD_INFO_COPY.otherBenefit]);
    expect(plan.more.find((q) => q.key === 'housing_type')).toMatchObject({ opens: [], completes: ['Apoyo de vivienda'] });
    // La pista recuerda el caso con datos de la ficha.
    // La pista recuerda el caso con datos de la ficha relevantes al campo y no se repite idéntica.
    expect(plan.primary[0]?.hint).toContain(ADD_INFO_COPY.hintRshBand('40'));
    expect(plan.primary[0]?.hint).toContain(ADD_INFO_COPY.hintStateUnknown('Subsidio Maternal'));
    expect(plan.primary[1]?.hint).toBeNull();
    expect(plan.more[0]?.hint).toContain(ADD_INFO_COPY.hintChildren('2', yearsLabel(1, '1')));

    const visible = [...plan.primary, ...plan.more].flatMap((q) => [...q.opens, ...q.completes, q.hint ?? '']);
    for (const text of visible) expect(text).not.toMatch(/\b(BEN|FAM)-/);
  });
});
