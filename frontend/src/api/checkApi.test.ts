// scripts/check-api.mjs contra el mock-servidor C3 (setupServer): OK por ruta, FAIL sin volcar bodies.
// Datos 100 % sintéticos (SYNTHETIC_DEMO_NOT_A_REAL_PERSON).
import { HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { resolveCheckBaseUrl, runApiCheck } from '../../scripts/check-api.mjs';
import { variants } from '../test/fixtures';
import { server, TEST_API_BASE } from '../test/mswServer';
import { overrideOperation } from '../test/operations';

describe('check:api', () => {
  it('valida todos los GET de C3 y reporta OK por ruta', async () => {
    const lines: string[] = [];
    const { ok, results } = await runApiCheck({ baseUrl: TEST_API_BASE, out: (line) => lines.push(line) });
    expect(ok).toBe(true);
    expect(results).toHaveLength(9);
    expect(lines.slice(0, -1).every((line) => line.startsWith('OK '))).toBe(true);
  });

  it('una respuesta fuera de contrato es FAIL con la ruta del schema, sin el body', async () => {
    server.use(overrideOperation('listFamiliasByJardin', () => HttpResponse.json(variants.familiasWithInvalidEnum() as Record<string, unknown>)));
    const lines: string[] = [];
    const { ok } = await runApiCheck({ baseUrl: TEST_API_BASE, out: (line) => lines.push(line) });
    expect(ok).toBe(false);
    const fail = lines.find((line) => line.includes('/jardines/{id}/familias'));
    expect(fail).toMatch(/^FAIL 200 GET \/jardines\/\{id\}\/familias — schema \//);
    expect(lines.join('\n')).not.toMatch(/FAM-SIM|JAR-SIM|SNAP-SIM/);
  });

  it('solo acepta URLs loopback terminadas en /api/v1', () => {
    expect(resolveCheckBaseUrl('http://127.0.0.1:8000/api/v1/')).toBe('http://127.0.0.1:8000/api/v1');
    expect(resolveCheckBaseUrl('https://api.example.org/api/v1')).toBeNull();
    expect(resolveCheckBaseUrl('http://localhost:8000/otra')).toBeNull();
  });
});
