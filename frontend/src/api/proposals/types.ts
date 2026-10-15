// Tipos de la operación PROPUESTA "Agregar información" (DEC-039, PREG-039). NO es C3: el schema
// cerrado vive en ./AddFamilyInfoRequestV1.schema.json y la respuesta es FamiliaDetailEnvelope de C3.
import type { PreevaluationRequest } from '../types';

/** Campos cerrados de PreevaluationRequest que se pueden declarar para una familia existente. */
export type AddInfoField = Exclude<keyof PreevaluationRequest, 'data_classification' | 'garden_id' | 'commune_id' | 'demo_notice_accepted'>;

/** Ausente = sin cambio; null = "No sé" (housing_type usa UNKNOWN). */
export type AddFamilyInfoRequestV1 = { readonly data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON' } & {
  readonly [K in AddInfoField]?: PreevaluationRequest[K];
};
