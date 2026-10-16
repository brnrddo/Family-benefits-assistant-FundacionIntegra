// Secciones de la ficha (Puede postular / Falta información / Ya postuló o sin cupo) en el orden de C3.
// Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { describe, expect, it } from 'vitest';
import type { BenefitResult, Opportunity, OpportunityListEnvelope } from '../api/types';
import { fichaBrecha, payloadOf } from '../test/fixtures';
import { benefitSections, visibleSections } from './benefitGroups';

describe('benefitSections', () => {
  it('reparte por estado, respeta el orden de la lista prioridad y omite NO_APLICA', () => {
    const detail = structuredClone(fichaBrecha().data);
    const extra: BenefitResult[] = [
      // Bug C: SI PRELIMINAR pendiente de antecedentes sin códigos (backend real).
      { benefit_id: 'BEN-012', result: 'SI', level: 'PRELIMINAR', access_state: 'PENDIENTE_ANTECEDENTES', missing_codes: [], trace: [] },
      { benefit_id: 'BEN-013', result: 'NO_APLICA', level: null, access_state: 'NO_APLICA', missing_codes: [], trace: [] },
      { benefit_id: 'BEN-014', result: 'SI', level: 'CONFIRMADO', access_state: 'SIN_CUPO', missing_codes: [], trace: [] },
      { benefit_id: 'BEN-015', result: 'SI', level: 'CONFIRMADO', access_state: 'GESTION_RECHAZADA', missing_codes: [], trace: [] },
    ];
    detail.benefit_results.push(...extra);
    const items = payloadOf<OpportunityListEnvelope>('listOportunidades.FAM-SIM-E3-00001.prioridad').items;
    const byId = (id: string) => items.find((o) => o.benefit_id === id) as Opportunity;
    // Orden de C3 distinto del catálogo.
    const prioridad = ['BEN-003', 'BEN-002', 'BEN-001', 'BEN-004'].map(byId);

    const sections = benefitSections(detail, prioridad);
    const ids = (rows: readonly { benefitId: string }[]) => rows.map((row) => row.benefitId);
    expect(ids(sections.apply)).toEqual(['BEN-002', 'BEN-001']);
    expect(ids(sections.missing)).toEqual(['BEN-003', 'BEN-012']);
    expect(ids(sections.done)).toEqual(['BEN-004', 'BEN-014', 'BEN-015']);
    expect(visibleSections(sections, 'all')).toEqual(['apply', 'missing', 'done']);
    expect(visibleSections(sections, 'done')).toEqual(['done']);
    expect(visibleSections({ ...sections, apply: [] }, 'all')).toEqual(['missing', 'done']);
  });
});
