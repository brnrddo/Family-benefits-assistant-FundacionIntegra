import { describe, expect, it } from 'vitest';
import { COPY_CATALOG } from '../i18n/catalog';
import * as presentation from './presentation';

const ACCESS_STATES = [
  'ASIGNADO',
  'GESTION_EN_CURSO',
  'GESTION_RECHAZADA',
  'ELEGIBLE_SIN_ASIGNACION',
  'SIN_CUPO',
  'PENDIENTE_ANTECEDENTES',
  'INDETERMINADO',
  'NO_APLICA',
] as const;

describe('domain/presentation', () => {
  it('§10.4: estado de acceso → grupo', () => {
    expect(presentation.accessGroup('ELEGIBLE_SIN_ASIGNACION')).toBe('go');
    expect(presentation.accessGroup('PENDIENTE_ANTECEDENTES')).toBe('ask');
    expect(presentation.accessGroup('INDETERMINADO')).toBe('ask');
    expect(presentation.accessGroup('ASIGNADO')).toBe('has');
    expect(presentation.accessGroup('GESTION_EN_CURSO')).toBe('has');
    expect(presentation.accessGroup('GESTION_RECHAZADA')).toBe('other');
    expect(presentation.accessGroup('SIN_CUPO')).toBe('other');
    expect(presentation.accessGroup('NO_APLICA')).toBeNull();
    expect(presentation.accessPresentation('NO_APLICA')).toBeNull();
    expect(presentation.accessPresentation('ASIGNADO')).toEqual({ icon: 'mailbox', tone: 'has', labelKey: 'group.has.label' });
    expect(presentation.accessPresentation('GESTION_EN_CURSO')?.icon).toBe('clock');
  });

  it('cubre todos los estados de acceso con ícono y texto', () => {
    expect(Object.keys(presentation.ACCESS_STATE_GROUP).sort()).toEqual([...ACCESS_STATES].sort());
    expect(Object.keys(presentation.ACCESS_STATE_KEY).sort()).toEqual([...ACCESS_STATES].sort());
  });

  it('SUP-036: chips de urgencia por umbral, sin alterar nada', () => {
    expect(presentation.urgencyChip(1)).toBe('chip.urgency.high');
    expect(presentation.urgencyChip(0.8)).toBe('chip.urgency.high');
    expect(presentation.urgencyChip(0.79)).toBe('chip.urgency.week');
    expect(presentation.urgencyChip(0.6)).toBe('chip.urgency.week');
    expect(presentation.urgencyChip(0.59)).toBeNull();
    expect(presentation.urgencyChip(0)).toBeNull();
  });

  it('semáforo con ícono, tono y clave para los 4 valores', () => {
    expect(Object.keys(presentation.TRAFFIC_LIGHT_PRESENTATION).sort()).toEqual(
      ['AMARILLO', 'AZUL', 'SIN_OPORTUNIDADES', 'VERDE'].sort(),
    );
    for (const value of Object.values(presentation.TRAFFIC_LIGHT_PRESENTATION)) {
      expect(value.icon).toBeTruthy();
      expect(value.labelKey in COPY_CATALOG).toBe(true);
    }
  });

  it('todas las claves de todos los mapeos existen en el catálogo i18n', () => {
    const maps = Object.entries(presentation).filter(
      ([name, value]) => /_(KEY|PRESENTATION)$/.test(name) && typeof value === 'object' && value !== null,
    );
    expect(maps.length).toBeGreaterThanOrEqual(18);
    for (const [, map] of maps) {
      for (const value of Object.values(map as Record<string, unknown>)) {
        const key = typeof value === 'string' ? value : (value as { labelKey: string }).labelKey;
        expect(key in COPY_CATALOG, key).toBe(true);
      }
    }
  });

  it('los mapeos cubren todos los valores de los enums C3', () => {
    expect(Object.keys(presentation.MISSING_CODE_KEY)).toHaveLength(19);
    expect(Object.keys(presentation.INCONSISTENCY_KEY)).toHaveLength(5);
    expect(Object.keys(presentation.NEXT_STEP_KEY)).toHaveLength(4);
    expect(Object.keys(presentation.CHANNEL_KEY)).toHaveLength(4);
    expect(Object.keys(presentation.RESULT_KEY)).toHaveLength(4);
    expect(Object.keys(presentation.ACTION_TYPE_KEY)).toHaveLength(4);
    expect(Object.keys(presentation.HOUSING_KEY)).toHaveLength(5);
    expect(Object.keys(presentation.INCOME_BAND_KEY)).toHaveLength(4);
    expect(Object.keys(presentation.CONVERSATION_STATUS_KEY)).toHaveLength(3);
    expect(Object.keys(presentation.KPI_LEVEL_KEY)).toHaveLength(4);
  });
});
