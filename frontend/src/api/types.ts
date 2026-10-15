// Alias de tipos C3 generados (src/api/generated/c3.d.ts). Nunca se escriben a mano.
import type { components, operations } from './generated/c3';

type Schemas = components['schemas'];

export type OperationId = keyof operations;
/** Operaciones PROPUESTAS por el frontend que aún NO están en C3 (src/api/proposals, DEC-039). */
export type ProposalOperationId = 'addFamiliaAntecedentes' | 'getCatalogoAlcance';
/** Lo que acepta el transporte: una operación C3 o una propuesta explícita. */
export type AnyOperationId = OperationId | ProposalOperationId;

export type Id = Schemas['Id'];
export type EnvelopeMetadata = Schemas['EnvelopeMetadata'];
export type CompositionMember = Schemas['CompositionMember'];
export type SourceCitation = Schemas['SourceCitation'];
export type TraceItem = Schemas['TraceItem'];
export type BenefitResult = Schemas['BenefitResult'];
export type Opportunity = Schemas['Opportunity'];
export type JardinSummary = Schemas['JardinSummary'];
export type FamilySummary = Schemas['FamilySummary'];
export type FamilyDetail = Schemas['FamilyDetail'];
export type FamilyContextView = Schemas['FamilyContextView'];
export type ConversationRecord = Schemas['ConversationRecord'];
export type PreevaluationResult = Schemas['PreevaluationResult'];
export type GapSummary = Schemas['GapSummary'];
export type KpiResult = Schemas['KpiResult'];
export type FlyerDraft = Schemas['FlyerDraft'];
export type PrintableCard = Schemas['PrintableCard'];
export type PrintableBenefitSection = Schemas['PrintableBenefitSection'];
export type ScriptContent = Schemas['ScriptContent'];
export type MessageContent = Schemas['MessageContent'];

export type JardinListEnvelope = Schemas['JardinListEnvelope'];
export type FamiliaListEnvelope = Schemas['FamiliaListEnvelope'];
export type FamiliaDetailEnvelope = Schemas['FamiliaDetailEnvelope'];
export type FamiliaContextEnvelope = Schemas['FamiliaContextEnvelope'];
export type OpportunityListEnvelope = Schemas['OpportunityListEnvelope'];
export type ScriptGenerationEnvelope = Schemas['ScriptGenerationEnvelope'];
export type MessageGenerationEnvelope = Schemas['MessageGenerationEnvelope'];
export type ConversationEnvelope = Schemas['ConversationEnvelope'];
export type PreevaluationEnvelope = Schemas['PreevaluationEnvelope'];
export type KpiEnvelope = Schemas['KpiEnvelope'];
export type AssistantEnvelope = Schemas['AssistantEnvelope'];
export type FlyerDraftEnvelope = Schemas['FlyerDraftEnvelope'];

export type FamilyGenerationPublicRequest = Schemas['FamilyGenerationPublicRequest'];
export type AssistantPublicRequest = Schemas['AssistantPublicRequest'];
export type ConversationRequest = Schemas['ConversationRequest'];
export type PreevaluationRequest = Schemas['PreevaluationRequest'];
export type TextractFlyerRequestV1 = NonNullable<operations['ingestSyntheticFlyer']['requestBody']>['content']['application/json'];
export type ErrorResponse = components['responses']['Error400']['content']['application/json'];

export type AccessState = BenefitResult['access_state'];
export type OpportunityAccessState = Opportunity['access_state'];
export type BenefitResultValue = BenefitResult['result'];
export type Level = NonNullable<BenefitResult['level']>;
export type ActionType = Opportunity['action_type'];
export type TrafficLight = FamilySummary['traffic_light'];
export type ConversationStatus = FamilySummary['conversation_status'];
export type Role = CompositionMember['role'];
export type PreferredFormat = FamilyContextView['preferred_format'];
export type MissingCode = FamilyContextView['missing_codes'][number];
export type InconsistencyCode = FamilyContextView['inconsistency_codes'][number];
export type IncomeBand = NonNullable<FamilyContextView['income_band']>;
export type HousingType = NonNullable<PreevaluationRequest['housing_type']>;
export type NextStep = ConversationRequest['next_step'];
export type Channel = ConversationRequest['channel'];
export type TraceResult = TraceItem['result'];
export type Zone = JardinSummary['zone'];
export type Provider = ScriptGenerationEnvelope['provider'];
export type AssistantIntent = AssistantEnvelope['intent'];
export type OpportunityOrder = 'prioridad' | 'urgencia' | 'beneficio';
export type KpiLevel = KpiResult['level'];

/** Resultado exitoso de una operación C3 (§6.2). `requestId` sale del cuerpo validado. */
export interface C3Ok<T> {
  readonly status: number;
  readonly body: T;
  readonly requestId: string | null;
  readonly receivedAt: string;
}
