// Caché Demo con TTL (FE-006). Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { validateFamiliaDetailEnvelope } from '../api/generated/validators.gen.js';
import { resetClock, setClock } from '../lib/now';
import { fichaBrecha } from '../test/fixtures';
import { installTestRuntime, resetTestRuntime } from '../test/runtime';
import { clearDemoData } from './db';
import { readCache, writeCache } from './demoCache';

const START = Date.parse('2026-10-14T10:00:00-03:00');

describe('caché Demo', () => {
  beforeEach(async () => {
    installTestRuntime({ persistence: true });
    await clearDemoData();
  });
  afterEach(async () => {
    resetClock();
    await clearDemoData();
    resetTestRuntime();
  });

  it('lee dentro del TTL, vence después y no escribe IDs no sintéticos', async () => {
    let current = START;
    setClock(() => current);
    const body = fichaBrecha();
    expect(await writeCache('familia:FAM-SIM-E3-00001', body, body.meta.snapshot_id)).toBe(true);
    expect((await readCache('familia:FAM-SIM-E3-00001', validateFamiliaDetailEnvelope))?.body).toEqual(body);

    current = START + 13 * 3_600_000; // TTL por defecto: 12 h
    expect(await readCache('familia:FAM-SIM-E3-00001', validateFamiliaDetailEnvelope)).toBeNull();

    const real = { ...body, data: { ...body.data, family_id: 'FAM-E3-00001' } };
    expect(await writeCache('familia:FAM-E3-00001', real, body.meta.snapshot_id)).toBe(false);
  });
});
