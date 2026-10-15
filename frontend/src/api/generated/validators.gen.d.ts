// GENERADO por scripts/gen-contract.mjs. No editar.
import type { components, operations } from './c3';

export type ValidateFn<T> = ((data: unknown) => data is T) & {
  errors?: { instancePath: string; keyword: string }[] | null;
};

export declare const validateAssistantEnvelope: ValidateFn<components['schemas']['AssistantEnvelope']>;
export declare const validateAssistantPublicRequest: ValidateFn<components['schemas']['AssistantPublicRequest']>;
export declare const validateConversationEnvelope: ValidateFn<components['schemas']['ConversationEnvelope']>;
export declare const validateConversationRequest: ValidateFn<components['schemas']['ConversationRequest']>;
export declare const validateErrorResponse: ValidateFn<components['responses']['Error400']['content']['application/json']>;
export declare const validateFamiliaContextEnvelope: ValidateFn<components['schemas']['FamiliaContextEnvelope']>;
export declare const validateFamiliaDetailEnvelope: ValidateFn<components['schemas']['FamiliaDetailEnvelope']>;
export declare const validateFamiliaListEnvelope: ValidateFn<components['schemas']['FamiliaListEnvelope']>;
export declare const validateFamilyGenerationPublicRequest: ValidateFn<components['schemas']['FamilyGenerationPublicRequest']>;
export declare const validateFlyerDraftEnvelope: ValidateFn<components['schemas']['FlyerDraftEnvelope']>;
export declare const validateJardinListEnvelope: ValidateFn<components['schemas']['JardinListEnvelope']>;
export declare const validateKpiEnvelope: ValidateFn<components['schemas']['KpiEnvelope']>;
export declare const validateMessageGenerationEnvelope: ValidateFn<components['schemas']['MessageGenerationEnvelope']>;
export declare const validateOpportunityListEnvelope: ValidateFn<components['schemas']['OpportunityListEnvelope']>;
export declare const validatePreevaluationEnvelope: ValidateFn<components['schemas']['PreevaluationEnvelope']>;
export declare const validatePreevaluationRequest: ValidateFn<components['schemas']['PreevaluationRequest']>;
export declare const validateScriptGenerationEnvelope: ValidateFn<components['schemas']['ScriptGenerationEnvelope']>;
export declare const validateTextractFlyerRequestV1: ValidateFn<NonNullable<operations['ingestSyntheticFlyer']['requestBody']>['content']['application/json']>;
