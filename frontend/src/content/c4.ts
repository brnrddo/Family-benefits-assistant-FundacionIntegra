// Capacidades Polly/Translate (design.md §7.5, FE-010, PREG-031). Solo se activan si C4 es VALID,
// el servicio está `enabled` con evidencia VERIFICADO_EN_CUENTA, smoke test, allowlist no vacía
// Y C3 tiene la ruta. C3 v1.0.2 no tiene rutas de audio ni traducción: hoy ambas son `false`.
import { accessibility, c4Status } from 'virtual:brujula-content';

export const C3_HAS_AUDIO_ROUTE = false;
export const C3_HAS_TRANSLATE_ROUTE = false;

type Accessibility = typeof accessibility;

export interface C4CapabilityInput {
  readonly c4Status: 'VALID' | 'MISSING' | 'INVALID';
  readonly accessibility: Accessibility;
}

export function audioAvailableFrom(input: C4CapabilityInput, c3HasRoute: boolean = C3_HAS_AUDIO_ROUTE): boolean {
  const polly = input.accessibility?.polly;
  return (
    input.c4Status === 'VALID' &&
    polly !== undefined &&
    polly.enabled &&
    polly.evidence_state === 'VERIFICADO_EN_CUENTA' &&
    typeof polly.smoke_test_evidence_id === 'string' &&
    polly.smoke_test_evidence_id !== '' &&
    polly.allowed_voices.length > 0 &&
    c3HasRoute
  );
}

export function translationAvailableFrom(input: C4CapabilityInput, c3HasRoute: boolean = C3_HAS_TRANSLATE_ROUTE): boolean {
  const translate = input.accessibility?.translate;
  return (
    input.c4Status === 'VALID' &&
    translate !== undefined &&
    translate.enabled &&
    translate.evidence_state === 'VERIFICADO_EN_CUENTA' &&
    typeof translate.smoke_test_evidence_id === 'string' &&
    translate.smoke_test_evidence_id !== '' &&
    translate.allowed_target_languages.length > 0 &&
    c3HasRoute
  );
}

export const audioAvailable: boolean = audioAvailableFrom({ c4Status, accessibility });
export const translationAvailable: boolean = translationAvailableFrom({ c4Status, accessibility });
