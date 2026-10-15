import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import meta from '../api/generated/c3.meta.json';
import {
  audioAvailable,
  audioAvailableFrom,
  C3_HAS_AUDIO_ROUTE,
  C3_HAS_TRANSLATE_ROUTE,
  translationAvailable,
  translationAvailableFrom,
  type C4CapabilityInput,
} from './c4';

function accessibility(overrides: { polly?: object; translate?: object } = {}): NonNullable<C4CapabilityInput['accessibility']> {
  return {
    canonical_spanish_label_key: 'a11y.canonical_spanish_label',
    polly: {
      enabled: true,
      evidence_state: 'VERIFICADO_EN_CUENTA',
      smoke_test_evidence_id: 'EVID-SIM-POLLY-001',
      allowed_voices: [{ voice_id: 'VozSim', language_code: 'es-CL' }],
      max_output_characters: 1000,
      fallback_label_key: 'a11y.audio_unavailable',
      ...overrides.polly,
    },
    translate: {
      enabled: true,
      evidence_state: 'VERIFICADO_EN_CUENTA',
      smoke_test_evidence_id: 'EVID-SIM-TRANSLATE-001',
      source_language: 'es',
      allowed_target_languages: ['ht'],
      max_output_characters: 1000,
      fallback_label_key: 'a11y.translation_unavailable',
      ...overrides.translate,
    },
  } as NonNullable<C4CapabilityInput['accessibility']>;
}

describe('content/c4 (§7.5)', () => {
  it('C3 v1.0.2 no tiene rutas de audio ni traducción (confirmado contra c3.d.ts)', () => {
    expect(C3_HAS_AUDIO_ROUTE).toBe(false);
    expect(C3_HAS_TRANSLATE_ROUTE).toBe(false);
    const dts = readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../api/generated/c3.d.ts'), 'utf8');
    const paths = [...dts.matchAll(/^ {4}"(\/[^"]*)": \{/gm)].map((m) => m[1] ?? '');
    // C3 v1.0.2: un path por operación.
    expect(paths).toHaveLength(Object.keys(meta.operations).length);
    expect(paths.some((p) => /audio|tts|polly|tradu|translat/i.test(p))).toBe(false);
  });

  it('hoy, sin ruta C3, audio y traducción quedan ocultos', () => {
    expect(audioAvailable).toBe(false);
    expect(translationAvailable).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility() })).toBe(false);
    expect(translationAvailableFrom({ c4Status: 'VALID', accessibility: accessibility() })).toBe(false);
  });

  it('ocultos con C4 ausente, inválido, sin evidencia, sin voces/idiomas o deshabilitado', () => {
    const valid = accessibility();
    expect(audioAvailableFrom({ c4Status: 'MISSING', accessibility: null }, true)).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'INVALID', accessibility: valid }, true)).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ polly: { evidence_state: 'NO_VERIFICADO' } }) }, true)).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ polly: { smoke_test_evidence_id: null } }) }, true)).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ polly: { allowed_voices: [] } }) }, true)).toBe(false);
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ polly: { enabled: false } }) }, true)).toBe(false);
    expect(translationAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ translate: { allowed_target_languages: [] } }) }, true)).toBe(false);
    expect(translationAvailableFrom({ c4Status: 'VALID', accessibility: accessibility({ translate: { enabled: false } }) }, true)).toBe(false);
  });

  it('solo con todo válido Y ruta C3 se activarían', () => {
    expect(audioAvailableFrom({ c4Status: 'VALID', accessibility: accessibility() }, true)).toBe(true);
    expect(translationAvailableFrom({ c4Status: 'VALID', accessibility: accessibility() }, true)).toBe(true);
  });
});
