// Snapshot OpenAPI de FE-T01 (§6.1): si C3 o sus schemas cambian sin regenerar, falla.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import meta from './generated/c3.meta.json';

// Rutas con node:path: Vite reescribe el patrón `new URL(relativa, import.meta.url)` como asset.
const HERE = path.dirname(fileURLToPath(import.meta.url));
const CONTRACTS_DIR = path.resolve(HERE, '../../../.kiro/specs/_shared/contracts');

function hashNormalized(relativePath: string): string {
  const text = readFileSync(path.join(CONTRACTS_DIR, ...relativePath.split('/')), 'utf8').replace(/\r\n/g, '\n');
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

describe('snapshot C3', () => {
  it('los hashes de C3 y sus refs coinciden con c3.meta.json', () => {
    const files = meta.files as Record<string, string>;
    expect(Object.keys(files)).toContain('C3-api.openapi.yaml');
    for (const [relativePath, expected] of Object.entries(files)) {
      expect(hashNormalized(relativePath), 'C3 cambió: ejecute npm run gen:contract y revise').toBe(expected);
    }
  });

  it('declara C3 v1.0.2 con 12 operaciones y un disclaimer único', () => {
    expect(meta.info_version).toBe('1.0.2');
    expect(Object.keys(meta.operations)).toHaveLength(12);
    expect(meta.disclaimer).toBe('Orientación referencial; no determina derechos. Confirmar en la institución.');
    expect(meta.operations.createConversacion.expectedStatus).toBe(201);
  });

  it('los validadores generados no contienen require ni evaluación dinámica', () => {
    const code = readFileSync(path.join(HERE, 'generated', 'validators.gen.js'), 'utf8');
    // Tokens armados por partes: security.static.test.ts recorre también este archivo.
    for (const token of [['requ', 'ire('], ['ev', 'al('], ['new Func', 'tion']]) {
      expect(code).not.toContain(token.join(''));
    }
    expect(code.startsWith('// GENERADO')).toBe(true);
  });
});
