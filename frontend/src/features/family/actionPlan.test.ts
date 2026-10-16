// "Qué hacer ahora" (determinista, sin LLM) y textos concretos de faltantes (bug C).
// Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { describe, expect, it } from 'vitest';
import type { BenefitRow } from '../../domain/benefitGroups';
import { knownMissingLabels } from '../../domain/presentation';
import { benefitName, t } from '../../i18n/copy';
import { buildActionPlan, toConfirmItems } from './actionPlan';
import { FAMILY_COPY } from './familyCopy';

function row(benefitId: string, over: Partial<BenefitRow> = {}): BenefitRow {
  return {
    benefitId,
    simpleTitle: null,
    result: 'SI',
    level: 'CONFIRMADO',
    accessState: 'ELEGIBLE_SIN_ASIGNACION',
    missingCodes: [],
    questions: [],
    opportunity: null,
    ...over,
  };
}

const missing = (benefitId: string, over: Partial<BenefitRow> = {}) =>
  row(benefitId, { result: 'INDETERMINADO', level: null, accessState: 'INDETERMINADO', ...over });

describe('buildActionPlan', () => {
  it('con faltantes: datos concretos sin repetir (máx. 3); con aplicables: entregar info de máx. 3', () => {
    const sections = {
      apply: ['BEN-001', 'BEN-002', 'BEN-006', 'BEN-007'].map((id) => row(id)),
      missing: [
        missing('BEN-003', { questions: ['¿Cuándo fue el último control?'] }),
        missing('BEN-005', { questions: ['¿cuándo fue el último control'] }),
        missing('BEN-009', { missingCodes: ['semanas_gestacion'] }),
        missing('BEN-010', { missingCodes: ['tramo_rsh'] }),
      ],
      done: [],
    };
    const plan = buildActionPlan(sections, { canAddInfo: true, scopes: new Map() });
    expect(plan.ask).toEqual({
      withForm: true,
      items: ['¿Cuándo fue el último control?', 'Semanas de embarazo', ...knownMissingLabels(['tramo_rsh'])],
    });
    expect(plan.deliver).toEqual(['BEN-001', 'BEN-002', 'BEN-006'].map((id) => benefitName(id, null)));
    expect(plan.none).toBe(false);

    const empty = buildActionPlan({ apply: [], missing: [], done: [row('BEN-004', { accessState: 'ASIGNADO' })] }, { canAddInfo: true, scopes: new Map() });
    expect(empty).toEqual({ ask: null, deliver: [], none: true });
  });

  it('guías sin campo: llevan el nombre del beneficio y el plan no manda al formulario', () => {
    const sections = { apply: [], missing: [missing('BEN-007', { missingCodes: ['estado_acceso', 'vigencia'] })], done: [] };
    const guide = FAMILY_COPY.benefitGuide(benefitName('BEN-007', null), knownMissingLabels(['estado_acceso', 'vigencia']));
    expect(guide).toBe(`${benefitName('BEN-007', null)}: si ya recibe o tramita el apoyo · si el apoyo sigue vigente`);
    expect(toConfirmItems(sections, null, new Map())).toEqual([guide]);
    expect(buildActionPlan(sections, { canAddInfo: true, scopes: new Map() }).ask).toEqual({ withForm: false, items: [guide] });
  });

  it('todo código conocido del motor o de C3 tiene texto propio (nunca el genérico)', () => {
    const codes = [
      'semanas_gestacion', 'cobertura_incompatible', 'parto_red_publica', 'control_prenatal_red_publica', 'tramo_rsh',
      'rsh_band', 'antecedente_edad_vigente', 'residencia_comuna', 'chile_crece_contigo_access', 'housing_type', 'pregnancy',
      'composition', 'estado_acceso', 'id_beneficio_o_programa', 'vigencia', 'dias_desde_nacimiento', 'documento_terapia_dias',
      'distancia_terapia_km', 'terapia_vigencia', 'dias_desde_evento', 'pago_previo_ben020', 'discapacidad_severidad',
      'discapacidad_vigencia', 'dias_desde_control',
    ];
    for (const code of codes) {
      const labels = knownMissingLabels([code]);
      expect(labels, code).toHaveLength(1);
      expect(labels[0], code).not.toBe(t('family.missing_generic'));
    }
    // Desconocido: se omite (sin genérico, sin el código).
    expect(knownMissingLabels(['codigo_desconocido'])).toEqual([]);
  });
});
