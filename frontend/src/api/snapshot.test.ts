import { describe, expect, it, vi } from 'vitest';
import { createSnapshotStore, snapshotIdOf, type SnapshotPersistence } from './snapshot';

function fakePersistence(known: string | null) {
  const calls: string[] = [];
  const persistence: SnapshotPersistence = {
    loadKnown: async () => known,
    saveKnown: async (id) => {
      calls.push(`save:${id}`);
    },
    purgeOtherSnapshots: async (keep) => {
      calls.push(`purge:${keep}`);
    },
  };
  return { persistence, calls };
}

describe('api/snapshot (§6.2)', () => {
  it('arranque sin persistencia (Escala): active y known nulos', async () => {
    const store = createSnapshotStore();
    await store.init({ persistence: null });
    expect(store.getState()).toEqual({ active: null, known: null });
  });

  it('primer meta distinto del conocido: purga sin invalidar ni toast, y persiste antes de resolver', async () => {
    const store = createSnapshotStore();
    const { persistence, calls } = fakePersistence('SNAP-SIM-DEMO-000');
    const effects = { invalidateAll: vi.fn(), notifyChanged: vi.fn() };
    await store.init({ persistence, effects });
    expect(store.getState()).toEqual({ active: null, known: 'SNAP-SIM-DEMO-000' });
    await expect(store.observe('SNAP-SIM-DEMO-001')).resolves.toBe('first');
    expect(calls).toEqual(['purge:SNAP-SIM-DEMO-001', 'save:SNAP-SIM-DEMO-001']);
    expect(effects.invalidateAll).not.toHaveBeenCalled();
    expect(effects.notifyChanged).not.toHaveBeenCalled();
    expect(store.getState()).toEqual({ active: 'SNAP-SIM-DEMO-001', known: 'SNAP-SIM-DEMO-001' });
  });

  it('cambio posterior: purga + invalida y avisa UNA vez aunque lleguen respuestas concurrentes', async () => {
    const store = createSnapshotStore();
    const { persistence } = fakePersistence(null);
    const effects = { invalidateAll: vi.fn(), notifyChanged: vi.fn() };
    await store.init({ persistence, effects });
    await store.observe('SNAP-SIM-DEMO-001');
    const results = await Promise.all([
      store.observe('SNAP-SIM-DEMO-002'),
      store.observe('SNAP-SIM-DEMO-002'),
      store.observe('SNAP-SIM-DEMO-002'),
    ]);
    expect(results).toEqual(['changed', 'same', 'same']);
    expect(effects.invalidateAll).toHaveBeenCalledTimes(1);
    expect(effects.notifyChanged).toHaveBeenCalledTimes(1);
  });

  it('envelope sin meta no toca el store', async () => {
    const store = createSnapshotStore();
    await store.init();
    const listener = vi.fn();
    store.subscribe(listener);
    await expect(store.observe(snapshotIdOf({ request_id: 'REQ-SIM-1', intent: 'CATALOG_INFO' }))).resolves.toBe('ignored');
    expect(listener).not.toHaveBeenCalled();
    expect(snapshotIdOf({ meta: { snapshot_id: 'SNAP-SIM-DEMO-001' } })).toBe('SNAP-SIM-DEMO-001');
  });
});
