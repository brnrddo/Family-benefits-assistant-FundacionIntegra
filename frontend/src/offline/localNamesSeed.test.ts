// Precarga local de nombres de trato INVENTADOS (DEC-047). Datos 100 % sintéticos
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON); ningún nombre corresponde a una persona real.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { FamiliaListEnvelope } from '../api/types';
import { SYNTHETIC_CLASSIFICATION } from '../config/profile';
import { isSyntheticId } from '../domain/ids';
import { FIXTURES } from '../test/fixtures';
import { installTestRuntime, resetTestRuntime } from '../test/runtime';
import { clearDemoData, openDemoDb } from './db';
import { clearLocalNamesMemory, currentLocalNames, cutLocalName, refreshLocalNames, saveLocalName } from './localNames';
import { seedLocalNames } from './localNamesSeed';
import seedFile from './localNamesSeed.json';

describe('precarga de nombres de trato (DEC-047)', () => {
  beforeEach(async () => {
    installTestRuntime({ persistence: true });
    await clearDemoData();
    await refreshLocalNames();
  });
  afterEach(async () => {
    clearLocalNamesMemory();
    await clearDemoData();
    resetTestRuntime();
  });

  it('el fixture es sintético, ya cortado, único y cubre todas las familias de los mocks', () => {
    expect(seedFile.data_classification).toBe(SYNTHETIC_CLASSIFICATION);
    expect(seedFile.names).toHaveLength(9);
    for (const { family_id, name } of seedFile.names) {
      expect(isSyntheticId(family_id), family_id).toBe(true);
      expect(cutLocalName(name)).toEqual({ ok: true, value: name });
    }
    const labels = seedFile.names.map((entry) => entry.name);
    expect(new Set(labels).size).toBe(labels.length);

    const seeded = new Set(seedFile.names.map((entry) => entry.family_id));
    const listed = Object.entries(FIXTURES)
      .filter(([key]) => key.startsWith('listFamiliasByJardin.'))
      .flatMap(([, fixture]) => (fixture.payload as FamiliaListEnvelope).items.map((item) => item.family_id));
    expect(listed.length).toBeGreaterThan(0);
    for (const familyId of listed) expect(seeded.has(familyId), familyId).toBe(true);
  });

  it('siembra con el store vacío, una sola vez y sin pisar lo que la tía guardó', async () => {
    expect(await seedLocalNames()).toBe(9);
    await refreshLocalNames();
    expect(currentLocalNames().size).toBe(9);
    expect(currentLocalNames().get('FAM-SIM-E3-00002')).toBe('Benjamín T.');

    expect(await seedLocalNames()).toBe(0);

    clearLocalNamesMemory();
    await clearDemoData();
    expect((await saveLocalName('FAM-SIM-E3-00001', 'Rosa Pérez')).ok).toBe(true);
    expect(await seedLocalNames()).toBe(0);
    await refreshLocalNames();
    expect([...currentLocalNames().entries()]).toEqual([['FAM-SIM-E3-00001', 'Rosa P.']]);
    const db = await openDemoDb();
    expect((await db.getAll('names')).map((record) => record.name)).toEqual(['Rosa P.']);
  });

  it('sin persistencia Demo no siembra ni lanza', async () => {
    resetTestRuntime();
    installTestRuntime();
    await expect(seedLocalNames()).resolves.toBe(0);
  });
});
