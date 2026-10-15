export interface paths {
    "/jardines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listJardines"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/jardines/{id}/familias": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listFamiliasByJardin"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["getFamilia"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}/contexto": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Devuelve vista minimizada y cerrada; nunca C2 crudo ni identificadores civiles. */
        get: operations["getContextoFamilia"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}/oportunidades": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["listOportunidades"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}/guion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description El cliente selecciona únicamente beneficios autorizados. El servidor carga C1/C2/C4, elige el prompt C4 y construye FamilyGenerationRequestV1 internamente. */
        post: operations["createGuion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}/mensaje": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description El cliente selecciona únicamente beneficios autorizados. El servidor carga C1/C2/C4, elige el prompt C4 y construye FamilyGenerationRequestV1 internamente. */
        post: operations["createMensaje"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/{id}/conversaciones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["createConversacion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/familias/nueva/preevaluacion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Campos cerrados de ficha sintética; sin mapa EAV, nombres, identificadores, contacto ni texto libre. Siempre PRELIMINAR. */
        post: operations["createPreevaluacion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/kpi": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["getKpi"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/asistente": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description El público envía solo una pregunta filtrable. El servidor recupera catálogo C4 y construye AssistantRequestV1 internamente. Elegibilidad individual no llama Bedrock. */
        post: operations["askCatalogAssistant"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/catalogo/ingesta-afiche": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description COULD. Solo asset sintético prepublicado; siempre queda pendiente de revisión humana. */
        post: operations["ingestSyntheticFlyer"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        Id: string;
        Hash: string;
        EnvelopeMetadata: {
            request_id: string;
            snapshot_id: components["schemas"]["Id"];
            eligibility_bundle_hash: components["schemas"]["Hash"];
            content_bundle_hash: components["schemas"]["Hash"];
            content_version: string;
        };
        CompositionMember: {
            /** @enum {string} */
            role: "ADULT_REFERENCE" | "CHILD" | "OTHER_ADULT";
            age: number;
        };
        SourceCitation: {
            source_id: components["schemas"]["Id"];
            /** Format: uri */
            url: string;
        };
        TraceItem: {
            rule_id: components["schemas"]["Id"];
            field: string;
            /** @enum {string} */
            operator: "EQ" | "LT" | "LTE" | "GT" | "GTE" | "IN" | "BETWEEN" | "ACTIVE_ON_DATE" | "RANGE_LOOKUP" | "REF_EQ" | "COUNT_REL_GTE" | "NOT_EXISTS_WITHIN";
            /** @enum {string} */
            result: "CUMPLE" | "NO_CUMPLE" | "INDETERMINADO";
        };
        BenefitResult: {
            benefit_id: components["schemas"]["Id"];
            /** @enum {string} */
            result: "SI" | "NO" | "INDETERMINADO" | "NO_APLICA";
            /** @enum {string|null} */
            level: "CONFIRMADO" | "PRELIMINAR" | null;
            /** @enum {string} */
            access_state: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES" | "INDETERMINADO" | "NO_APLICA";
            missing_codes: string[];
            trace: components["schemas"]["TraceItem"][];
        } & ({
            /** @constant */
            result?: "SI";
            /** @enum {string} */
            level?: "CONFIRMADO" | "PRELIMINAR";
            /** @enum {string} */
            access_state?: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES";
        } | {
            /** @constant */
            result?: "INDETERMINADO";
            /** @constant */
            level?: unknown;
            /** @constant */
            access_state?: "INDETERMINADO";
        } | {
            /** @enum {string} */
            result?: "NO" | "NO_APLICA";
            /** @constant */
            level?: unknown;
            /** @constant */
            access_state?: "NO_APLICA";
        });
        Opportunity: {
            benefit_id: components["schemas"]["Id"];
            simple_title: string;
            /** @enum {string} */
            result: "SI" | "INDETERMINADO";
            /** @enum {string|null} */
            level: "CONFIRMADO" | "PRELIMINAR" | null;
            /** @enum {string} */
            access_state: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES" | "INDETERMINADO";
            urgency: number;
            benefit: number;
            vulnerability: number;
            score: number;
            position: number;
            estimated_annual_amount: number | null;
            benefit_estimated: boolean;
            /** @enum {string} */
            action_type: "FAMILY_ACTION" | "AUTOMATIC" | "FOLLOW_UP" | "ASK_FIRST";
            why_first: string;
            missing_codes: string[];
            suggested_questions: string[];
            where_to_go: string | null;
            sources: components["schemas"]["SourceCitation"][];
        } & ({
            /** @constant */
            result?: "SI";
            /** @enum {string} */
            level?: "CONFIRMADO" | "PRELIMINAR";
            /** @enum {string} */
            access_state?: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES";
        } | {
            /** @constant */
            result?: "INDETERMINADO";
            /** @constant */
            level?: unknown;
            /** @constant */
            access_state?: "INDETERMINADO";
        });
        JardinSummary: {
            garden_id: components["schemas"]["Id"];
            commune_id: components["schemas"]["Id"];
            region_id: components["schemas"]["Id"];
            /** @enum {string} */
            zone: "URBANA" | "RURAL";
            families_total: number;
            families_informed: number;
            informed_percentage: number | null;
        };
        FamilySummary: {
            family_id: components["schemas"]["Id"];
            priority_score: number;
            vulnerability: number;
            opportunity_count: number;
            /** @enum {string} */
            conversation_status: "PENDIENTE" | "CONVERSADA" | "EN_COLA";
            /** @enum {string} */
            traffic_light: "VERDE" | "AMARILLO" | "AZUL" | "SIN_OPORTUNIDADES";
            top_benefit_ids: components["schemas"]["Id"][];
        };
        FamilyDetail: {
            family_id: components["schemas"]["Id"];
            garden_id: components["schemas"]["Id"];
            composition: components["schemas"]["CompositionMember"][];
            /** @enum {integer|null} */
            rsh_band: 40 | 50 | 60 | 70 | 80 | 90 | 100 | null;
            informed: boolean;
            top_opportunities: components["schemas"]["Opportunity"][];
            benefit_results: components["schemas"]["BenefitResult"][];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
        };
        FamilyContextView: {
            family_id: components["schemas"]["Id"];
            composition: components["schemas"]["CompositionMember"][];
            /** @enum {integer|null} */
            rsh_band: 40 | 50 | 60 | 70 | 80 | 90 | 100 | null;
            /** @enum {string|null} */
            income_band: "UNDER_110K" | "110K_250K" | "250K_400K" | "OVER_400K" | null;
            /** @enum {string} */
            preferred_format: "TEXT" | "VISUAL" | "AUDIO";
            language: string;
            urgency_signals: {
                recent_emergency: boolean | null;
                limited_quota: boolean | null;
                precarious_housing: boolean | null;
            };
            vulnerability_signals: {
                rsh_score: number | null;
                income_score: number | null;
                possible_child_disability: boolean | null;
            };
            inconsistency_codes: ("SIBLINGS_UNDER_6_MISMATCH" | "SIBLINGS_6_14_MISMATCH" | "SIBLINGS_15_18_MISMATCH" | "RSH_STATUS_MISMATCH" | "HOUSEHOLD_SIZE_MISMATCH")[];
            missing_codes: ("composition" | "child_age" | "siblings_under_6" | "siblings_6_14" | "siblings_15_18" | "rsh_status" | "rsh_band" | "income_band" | "ssyo_participation" | "chile_crece_contigo_access" | "last_health_control_date" | "possible_disability" | "therapy" | "housing_type" | "pregnancy" | "adult_over_65" | "employment_or_pension" | "water_difficulty" | "food_difficulty")[];
        };
        FamilyGenerationPublicRequest: {
            benefit_ids: components["schemas"]["Id"][];
        };
        AssistantPublicRequest: {
            question: string;
        };
        ConversationRequest: {
            benefit_ids: components["schemas"]["Id"][];
            /** @enum {string} */
            next_step: "GO_TO_INSTITUTION" | "UPDATE_RSH" | "BRING_DOCUMENTS" | "NONE";
            /** @enum {string} */
            channel: "IN_PERSON" | "GROUP_MEETING" | "WHATSAPP_PREVIEW" | "PRINTED";
            /** Format: date-time */
            occurred_at: string;
            snapshot_id: components["schemas"]["Id"];
            /** @enum {string} */
            origin: "REAL_DEMO" | "SIMULADO_DEMO";
        };
        PreevaluationRequest: {
            /** @constant */
            data_classification: "SYNTHETIC_DEMO_NOT_A_REAL_PERSON";
            garden_id: components["schemas"]["Id"];
            commune_id: components["schemas"]["Id"];
            /** @constant */
            demo_notice_accepted: true;
            child_age?: number | null;
            siblings_under_6?: number | null;
            siblings_6_14?: number | null;
            siblings_15_18?: number | null;
            has_rsh?: boolean | null;
            /** @enum {integer|null} */
            rsh_band?: 40 | 50 | 60 | 70 | 80 | 90 | 100 | null;
            /** @enum {string|null} */
            household_income_band?: "UNDER_110K" | "110K_250K" | "250K_400K" | "OVER_400K" | null;
            ssyo_participation?: boolean | null;
            chile_crece_contigo_access?: boolean | null;
            /** Format: date */
            last_child_health_control_date?: string | null;
            child_possible_disability?: boolean | null;
            child_in_therapy?: boolean | null;
            /** @enum {string|null} */
            housing_type?: "ADEQUATE" | "CAMP_OR_OCCUPATION" | "ROOM_IN_OTHER_HOME" | "OTHER" | "UNKNOWN" | null;
            household_pregnancy?: boolean | null;
            household_has_adult_over_65?: boolean | null;
            household_formal_employment_or_pension?: boolean | null;
            household_water_payment_difficulty?: boolean | null;
            household_food_purchase_difficulty?: boolean | null;
        };
        ConversationRecord: {
            /** Format: uuid */
            conversation_id: string;
            family_id: components["schemas"]["Id"];
            garden_id: components["schemas"]["Id"];
            benefit_ids: components["schemas"]["Id"][];
            /** @enum {string} */
            next_step: "GO_TO_INSTITUTION" | "UPDATE_RSH" | "BRING_DOCUMENTS" | "NONE";
            /** @enum {string} */
            channel: "IN_PERSON" | "GROUP_MEETING" | "WHATSAPP_PREVIEW" | "PRINTED";
            /** Format: date-time */
            occurred_at: string;
            snapshot_id: components["schemas"]["Id"];
            /** @enum {string} */
            origin: "REAL_DEMO" | "SIMULADO_DEMO";
            /** @enum {string} */
            status: "CONFIRMED";
        };
        PreevaluationResult: {
            family_id: components["schemas"]["Id"];
            /** @constant */
            level: "PRELIMINAR";
            /** Format: date-time */
            created_at: string;
            opportunities: components["schemas"]["Opportunity"][];
            questions: string[];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
        };
        GapSummary: {
            benefit_id: components["schemas"]["Id"];
            family_count: number;
            potential_annual_amount: number | null;
        };
        KpiResult: {
            /** @enum {string} */
            level: "jardin" | "comuna" | "region" | "nacional";
            scope_id: components["schemas"]["Id"] | null;
            /** Format: date */
            period_start: string;
            /** Format: date */
            period_end: string;
            total_families: number;
            informed_families: number;
            informed_percentage: number | null;
            total_new_families: number;
            informed_new_families: number;
            informed_new_percentage: number | null;
            opportunity_coverage_percentage: number | null;
            suppressed: boolean;
            top_gaps: components["schemas"]["GapSummary"][];
            /** Format: date-time */
            calculated_at: string;
            /** Format: date-time */
            watermark: string;
        };
        FlyerDraft: {
            draft_id: components["schemas"]["Id"];
            synthetic_asset_id: components["schemas"]["Id"];
            /** @enum {string} */
            status: "PENDIENTE_REVISION" | "REQUIERE_REVISION";
            confidence: number;
            name: string | null;
            institution: string | null;
            requirements: string | null;
            commune_id: components["schemas"]["Id"] | null;
            /** Format: date */
            valid_from: string | null;
            /** Format: date */
            valid_until: string | null;
            public_contact: string | null;
            /** @enum {string|null} */
            benefit_type: "MONETARY" | "IN_KIND" | "SERVICE" | null;
            warnings: string[];
        };
        GenerationBase: {
            meta: components["schemas"]["EnvelopeMetadata"];
            /** @enum {string} */
            provider: "BEDROCK" | "PLANTILLA";
            warnings: string[];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
        };
        ScriptContent: {
            benefit_ids: components["schemas"]["Id"][];
            script: string;
        };
        /** @description Texto estructurado sin markup; el frontend lo escapa y lo renderiza con su plantilla propia. */
        PrintableBenefitSection: {
            benefit_id: components["schemas"]["Id"];
            heading: string;
            reason: string;
            action: string;
            where_to_go: string | null;
            sources: components["schemas"]["SourceCitation"][];
        };
        /** @description Datos para CARD_V1; nunca contiene HTML, CSS, atributos, handlers ni URLs fuera de SourceCitation. */
        PrintableCard: {
            /** @constant */
            format_version: "CARD_V1";
            title: string;
            introduction: string;
            sections: components["schemas"]["PrintableBenefitSection"][];
        };
        MessageContent: {
            benefit_ids: components["schemas"]["Id"][];
            whatsapp_preview: string;
            printable_card: components["schemas"]["PrintableCard"];
        };
        ScriptGenerationEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            /** @enum {string} */
            provider: "BEDROCK" | "PLANTILLA";
            warnings: string[];
            content: components["schemas"]["ScriptContent"];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
        };
        MessageGenerationEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            /** @enum {string} */
            provider: "BEDROCK" | "PLANTILLA";
            warnings: string[];
            content: components["schemas"]["MessageContent"];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
        };
        AssistantEnvelope: {
            request_id: string;
            /** @enum {string} */
            intent: "CATALOG_INFO" | "REQUIRES_DETERMINISTIC_EVALUATION";
            answer: string;
            citations: components["schemas"]["SourceCitation"][];
            /** @constant */
            disclaimer: "Orientación referencial; no determina derechos. Confirmar en la institución.";
            /** @enum {string} */
            provider: "BEDROCK" | "PLANTILLA";
            warnings: string[];
        };
        JardinListEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            items: components["schemas"]["JardinSummary"][];
            next_cursor: string | null;
        };
        FamiliaListEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            items: components["schemas"]["FamilySummary"][];
            next_cursor: string | null;
        };
        OpportunityListEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            items: components["schemas"]["Opportunity"][];
            next_cursor: string | null;
        };
        FamiliaDetailEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["FamilyDetail"];
        };
        FamiliaContextEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["FamilyContextView"];
        };
        ConversationEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["ConversationRecord"];
        };
        PreevaluationEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["PreevaluationResult"];
        };
        KpiEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["KpiResult"];
        };
        FlyerDraftEnvelope: {
            meta: components["schemas"]["EnvelopeMetadata"];
            data: components["schemas"]["FlyerDraft"];
        };
        /** @description Solo servidor; se construye desde C1/C2 minimizado/C4 y nunca es request público. */
        InternalFamilyGenerationEnvelope: components["schemas"]["FamilyGenerationRequestV1.schema"];
        /** @description Solo servidor; catálogo y prompt provienen de C4, nunca del cliente. */
        InternalAssistantEnvelope: components["schemas"]["AssistantRequestV1.schema"];
        /** ErrorResponse */
        "ErrorResponse.schema": {
            error: {
                code: string;
                message: string;
                request_id: string;
                retryable: boolean;
                details: {
                    field: string;
                    reason: string;
                }[];
            };
        };
        /**
         * TextractFlyerRequestV1
         * @description Solo metadata de un asset sintético prepublicado e inventariado; prohíbe bytes, base64, URL o clave S3 del cliente.
         */
        "TextractFlyerRequestV1.schema": {
            synthetic_asset_id: string;
            /** @enum {unknown} */
            media_type: "image/jpeg" | "image/png";
            sha256: string;
        };
        benefit: {
            benefit_id: string;
            /** @enum {unknown} */
            result: "SI" | "INDETERMINADO";
            /** @enum {string|null} */
            level: "CONFIRMADO" | "PRELIMINAR" | null;
            /** @enum {unknown} */
            access_state: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES" | "INDETERMINADO";
            reason_codes: string[];
            missing_codes: string[];
            amount: number | null;
            source_ids: string[];
        };
        /** LlmContextV1 */
        "LlmContextV1.schema": {
            composition: {
                /** @enum {unknown} */
                role: "ADULT_REFERENCE" | "CHILD" | "OTHER_ADULT";
                age: number;
            }[];
            /** @enum {integer|null} */
            rsh_band: 40 | 50 | 60 | 70 | 80 | 90 | 100 | null;
            /** @enum {string|null} */
            income_band: "UNDER_110K" | "110K_250K" | "250K_400K" | "OVER_400K" | null;
            /** @enum {unknown} */
            preferred_format: "TEXT" | "VISUAL" | "AUDIO";
            language: string;
            benefits: components["schemas"]["benefit"][];
            $defs: {
                benefit: {
                    benefit_id: string;
                    /** @enum {unknown} */
                    result: "SI" | "INDETERMINADO";
                    /** @enum {string|null} */
                    level: "CONFIRMADO" | "PRELIMINAR" | null;
                    /** @enum {unknown} */
                    access_state: "ASIGNADO" | "GESTION_EN_CURSO" | "GESTION_RECHAZADA" | "ELEGIBLE_SIN_ASIGNACION" | "SIN_CUPO" | "PENDIENTE_ANTECEDENTES" | "INDETERMINADO";
                    reason_codes: string[];
                    missing_codes: string[];
                    amount: number | null;
                    source_ids: string[];
                };
            };
        };
        catalogItem: {
            benefit_id: string;
            title: string;
            description: string;
            actions: string[];
            institution: string;
            /** Format: uri */
            official_url: string;
            source_ids: string[];
        };
        /**
         * FamilyGenerationRequestV1 — envelope interno
         * @description Contrato interno construido por el servidor desde C1, C2 minimizado y C4 autorizados. Nunca se acepta como cuerpo público C3.
         */
        "FamilyGenerationRequestV1.schema": {
            /** @enum {unknown} */
            operation: "EXPLANATION" | "SCRIPT" | "FAMILY_MESSAGE";
            context: components["schemas"]["LlmContextV1.schema"];
            catalog_items: components["schemas"]["catalogItem"][];
            prompt_template_id: string;
            prompt_version: string;
            output_schema_version: string;
            $defs: {
                catalogItem: {
                    benefit_id: string;
                    title: string;
                    description: string;
                    actions: string[];
                    institution: string;
                    /** Format: uri */
                    official_url: string;
                    source_ids: string[];
                };
            };
        };
        /**
         * AssistantRequestV1 — envelope interno
         * @description Contrato interno construido por el servidor con pregunta filtrada, recuperación y prompt C4. El cliente público solo aporta la pregunta.
         */
        "AssistantRequestV1.schema": {
            /** @constant */
            operation: "CATALOG_ASSISTANT";
            question: string;
            catalog_items: {
                benefit_id: string;
                title: string;
                description: string;
                /** Format: uri */
                official_url: string;
                source_ids: string[];
            }[];
            prompt_template_id: string;
            prompt_version: string;
            output_schema_version: string;
        };
    };
    responses: {
        /** @description Jardines autorizados con conteos cerrados */
        JardinListResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["JardinListEnvelope"];
            };
        };
        /** @description Familias autorizadas priorizadas */
        FamiliaListResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["FamiliaListEnvelope"];
            };
        };
        /** @description Ficha minimizada, top tres y resultados técnicos */
        FamiliaDetailResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["FamiliaDetailEnvelope"];
            };
        };
        /** @description Contexto familiar minimizado y cerrado */
        FamiliaContextResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["FamiliaContextEnvelope"];
            };
        };
        /** @description Oportunidades con U/B/V y posición deterministas */
        OpportunityListResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["OpportunityListEnvelope"];
            };
        };
        /** @description Guion validado o fallback de plantilla */
        ScriptGenerationResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ScriptGenerationEnvelope"];
            };
        };
        /** @description Vista previa y tarjeta validada o fallback de plantilla */
        MessageGenerationResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["MessageGenerationEnvelope"];
            };
        };
        /** @description Conversación confirmada idempotentemente */
        ConversationResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ConversationEnvelope"];
            };
        };
        /** @description Resultado preliminar de ficha sintética */
        PreevaluationResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["PreevaluationEnvelope"];
            };
        };
        /** @description KPI agregado con nulos y supresión explícitos */
        KpiResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["KpiEnvelope"];
            };
        };
        /** @description Información general o redirección a evaluación determinista */
        AssistantResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["AssistantEnvelope"];
            };
        };
        /** @description Borrador sintético que exige revisión humana */
        FlyerDraftResponse: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["FlyerDraftEnvelope"];
            };
        };
        BadRequest: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Unauthorized: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Forbidden: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        NotFound: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Conflict: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Unprocessable: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Throttled: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        Unavailable: {
            headers: {
                [name: string]: unknown;
            };
            content?: never;
        };
        /** @description JSON o MIME inválido */
        Error400: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Autenticación ausente o inválida */
        Error401: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Operación no permitida sobre recurso visible */
        Error403: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Recurso inexistente o fuera de scope */
        Error404: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Idempotencia */
        Error409: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Semántica */
        Error422: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Límite de solicitudes */
        Error429: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
        /** @description Dependencia sin fallback seguro */
        Error503: {
            headers: {
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ErrorResponse.schema"];
            };
        };
    };
    parameters: {
        Id: components["schemas"]["Id"];
        Limit: number;
        Cursor: string;
        IdempotencyKey: string;
    };
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    listJardines: {
        parameters: {
            query?: {
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["JardinListResponse"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            429: components["responses"]["Throttled"];
        };
    };
    listFamiliasByJardin: {
        parameters: {
            query?: {
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["FamiliaListResponse"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            429: components["responses"]["Throttled"];
        };
    };
    getFamilia: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["FamiliaDetailResponse"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
        };
    };
    getContextoFamilia: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["FamiliaContextResponse"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
        };
    };
    listOportunidades: {
        parameters: {
            query?: {
                orden?: "prioridad" | "urgencia" | "beneficio";
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["OpportunityListResponse"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
        };
    };
    createGuion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FamilyGenerationPublicRequest"];
            };
        };
        responses: {
            200: components["responses"]["ScriptGenerationResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
            422: components["responses"]["Unprocessable"];
            429: components["responses"]["Throttled"];
            503: components["responses"]["Unavailable"];
        };
    };
    createMensaje: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FamilyGenerationPublicRequest"];
            };
        };
        responses: {
            200: components["responses"]["MessageGenerationResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
            422: components["responses"]["Unprocessable"];
            429: components["responses"]["Throttled"];
            503: components["responses"]["Unavailable"];
        };
    };
    createConversacion: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": components["parameters"]["IdempotencyKey"];
            };
            path: {
                id: components["parameters"]["Id"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationRequest"];
            };
        };
        responses: {
            201: components["responses"]["ConversationResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            404: components["responses"]["NotFound"];
            409: components["responses"]["Conflict"];
            422: components["responses"]["Unprocessable"];
            503: components["responses"]["Unavailable"];
        };
    };
    createPreevaluacion: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": components["parameters"]["IdempotencyKey"];
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PreevaluationRequest"];
            };
        };
        responses: {
            200: components["responses"]["PreevaluationResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            409: components["responses"]["Conflict"];
            422: components["responses"]["Unprocessable"];
        };
    };
    getKpi: {
        parameters: {
            query: {
                nivel: "jardin" | "comuna" | "region" | "nacional";
                id?: components["schemas"]["Id"];
                desde?: string;
                hasta?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["KpiResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            422: components["responses"]["Unprocessable"];
        };
    };
    askCatalogAssistant: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssistantPublicRequest"];
            };
        };
        responses: {
            200: components["responses"]["AssistantResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            422: components["responses"]["Unprocessable"];
            429: components["responses"]["Throttled"];
            503: components["responses"]["Unavailable"];
        };
    };
    ingestSyntheticFlyer: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextractFlyerRequestV1.schema"];
            };
        };
        responses: {
            200: components["responses"]["FlyerDraftResponse"];
            400: components["responses"]["BadRequest"];
            401: components["responses"]["Unauthorized"];
            403: components["responses"]["Forbidden"];
            409: components["responses"]["Conflict"];
            422: components["responses"]["Unprocessable"];
            429: components["responses"]["Throttled"];
            503: components["responses"]["Unavailable"];
        };
    };
}
