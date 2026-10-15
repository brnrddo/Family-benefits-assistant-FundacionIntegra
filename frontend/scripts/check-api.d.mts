// Tipos de scripts/check-api.mjs (para la prueba src/api/checkApi.test.ts).
export declare const DEFAULT_API_CHECK_URL: string;

export declare function resolveCheckBaseUrl(raw: string): string | null;

export interface ApiCheckResult {
  readonly route: string;
  readonly ok: boolean;
  readonly status: number | null;
  readonly detail: string | null;
}

export declare function runApiCheck(options: {
  baseUrl: string;
  fetchImpl?: typeof fetch;
  out?: (line: string) => void;
}): Promise<{ ok: boolean; results: ApiCheckResult[] }>;
