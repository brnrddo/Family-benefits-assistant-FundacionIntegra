// Tipos de las operaciones PROPUESTAS (NO son C3): "Agregar información" (DEC-039, PREG-039; schema
// cerrado en ./AddFamilyInfoRequestV1.schema.json, respuesta FamiliaDetailEnvelope de C3) y "alcance
// territorial" (DEC-072; respuesta cerrada en ./CatalogScopeEnvelopeV1.schema.json).
import type { EnvelopeMetadata, PreevaluationRequest } from '../types';

/** Campos cerrados de PreevaluationRequest que se pueden declarar para una familia existente. */
export type AddInfoField = Exclude<keyof PreevaluationRequest, 'data_classification' | 'garden_id' | 'commune_id' | 'demo_notice_accepted'>;

/** Ausente = sin cambio; null = "No sé" (housing_type usa UNKNOWN). */
export type AddFamilyInfoRequestV1 = { readonly data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON' } & {
  readonly [K in AddInfoField]?: PreevaluationRequest[K];
};

/** DEC-072: LOCAL = la regla vigente restringe la comuna de residencia; si no, NACIONAL. */
export type TerritorialScope = 'NACIONAL' | 'LOCAL';

/** Nivel catálogo: sin IDs ni nombres de comuna y sin IDs de familia. */
export interface CatalogScopeItem {
  readonly benefit_id: string;
  readonly scope: TerritorialScope;
  readonly simple_title: string;
  /** Beneficio inventado SOLO DEMO (no existe). */
  readonly demo: boolean;
}

export interface CatalogScopeEnvelopeV1 {
  readonly meta: EnvelopeMetadata;
  readonly items: readonly CatalogScopeItem[];
}
