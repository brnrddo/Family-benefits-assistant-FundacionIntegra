import { describe, expect, it } from 'vitest';
import { isSyntheticId, isValidId } from './ids';

describe('domain/ids', () => {
  it('acepta IDs C3 válidos', () => {
    for (const id of ['JAR-SIM-E3-00001', 'FAM-SIM-E3-00001', 'BEN-001', 'A', '0_X', 'X'.repeat(80)]) {
      expect(isValidId(id)).toBe(true);
    }
  });

  it('rechaza IDs inválidos', () => {
    for (const id of ['', 'x', '-ABC', 'AB C', 'AB/C', '../ETC', 'ABC%2F', 'X'.repeat(81), 'Ñ', 1, null, undefined]) {
      expect(isValidId(id)).toBe(false);
    }
  });

  it('isSyntheticId exige -SIM-', () => {
    expect(isSyntheticId('JAR-SIM-E3-00001')).toBe(true);
    expect(isSyntheticId('FAM-SIM-E3-00003')).toBe(true);
    expect(isSyntheticId('FAM-E3-00003')).toBe(false);
    expect(isSyntheticId('fam-sim-e3')).toBe(false);
  });
});
