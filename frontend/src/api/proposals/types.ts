// Tipos de las operaciones PROPUESTAS (NO son C3): "Agregar información" (DEC-039, PREG-039; schema
// cerrado en ./AddFamilyInfoRequestV1.schema.json, respuesta FamiliaDetailEnvelope de C3) y "alcance
// territorial" (DEC-072; respuesta cerrada en ./CatalogScopeEnvelopeV1.schema.json).
import type { EnvelopeMetadata, PreevaluationRequest } from '../types';

/** Campos cerrados de PreevaluationRequest que se pueden declarar para una familia existente. */
export type C3AddInfoField = Exclude<keyof PreevaluationRequest, 'data_classification' | 'garden_id' | 'commune_id' | 'demo_notice_accepted'>;

/** Booleanos de la propuesta FUERA de C3, para códigos del motor sin campo en PreevaluationRequest. */
export const ADD_INFO_EXTRA_FIELDS = [
  'pregnancy_weeks_at_least_threshold',
  'has_incompatible_coverage',
  'pregnancy_public_network_delivery',
  'pregnancy_public_prenatal_control',
  'residence_requirement_met',
  'age_record_current',
] as const;
export type AddInfoExtraField = (typeof ADD_INFO_EXTRA_FIELDS)[number];

export type AddInfoField = C3AddInfoField | AddInfoExtraField;

/** Ausente = sin cambio; null = "No sé" (housing_type usa UNKNOWN). */
export type AddFamilyInfoRequestV1 = { readonly data_classification: 'SYNTHETIC_DEMO_NOT_A_REAL_PERSON' } & {
  readonly [K in C3AddInfoField]?: PreevaluationRequest[K];
} & {
  readonly [K in AddInfoExtraField]?: boolean | null;
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
