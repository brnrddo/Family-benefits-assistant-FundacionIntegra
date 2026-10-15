/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_PROFILE: string;
  readonly VITE_USE_MOCKS: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_AUTH_MODE: string;
  readonly VITE_COGNITO_AUTHORITY: string;
  readonly VITE_COGNITO_DOMAIN: string;
  readonly VITE_COGNITO_CLIENT_ID: string;
  readonly VITE_COGNITO_SCOPES: string;
  readonly VITE_COGNITO_REDIRECT_PATH: string;
  readonly VITE_DATA_CLASSIFICATION: string;
  readonly VITE_DEMO_CACHE_TTL_HOURS: string;
  readonly VITE_PROPOSAL_ADD_INFO: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** Módulo virtual del plugin vite-plugins/brujula-content.ts (§7.2). Solo datos serializables. */
declare module 'virtual:brujula-content' {
  export const copyValues: Readonly<Record<string, string>>;
  export const copySource: 'CANONICAL' | 'MOCK_LOCAL' | 'MIXED';
  export const c4Status: 'VALID' | 'MISSING' | 'INVALID';
  export const contentVersion: string | null;
  /** Bloque `accessibility` de C4, solo cuando c4Status === 'VALID'. */
  export const accessibility: {
    readonly canonical_spanish_label_key: string;
    readonly polly: {
      readonly enabled: boolean;
      readonly evidence_state: 'NO_VERIFICADO' | 'NO_DISPONIBLE' | 'VERIFICADO_EN_CUENTA';
      readonly smoke_test_evidence_id: string | null;
      readonly allowed_voices: readonly { readonly voice_id: string; readonly language_code: string }[];
      readonly max_output_characters: number;
      readonly fallback_label_key: string;
    };
    readonly translate: {
      readonly enabled: boolean;
      readonly evidence_state: 'NO_VERIFICADO' | 'NO_DISPONIBLE' | 'VERIFICADO_EN_CUENTA';
      readonly smoke_test_evidence_id: string | null;
      readonly source_language: 'es';
      readonly allowed_target_languages: readonly string[];
      readonly max_output_characters: number;
      readonly fallback_label_key: string;
    };
  } | null;
  export const kpiMaxQueryDays: number | null;
}
