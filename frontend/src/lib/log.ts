// Única vía de logs del frontend (§6.4, PRIVACIDAD_DEMO.md "Logs y evidencia").
// En producción es no-op. En desarrollo solo emite campos de una allowlist: nunca
// bodies, preguntas, respuestas, nombres, tokens, URLs completas ni valores de entrada.

export interface LogFields {
  /** operationId C3 o nombre lógico de la operación. */
  readonly op?: string;
  /** Ruta normalizada, p. ej. `/familias/{id}` (nunca con IDs reales). */
  readonly route?: string;
  readonly status?: number;
  readonly kind?: string;
  readonly reason?: string;
  readonly requestId?: string | null;
  readonly ms?: number;
  readonly instancePath?: string;
  readonly keyword?: string;
  /** Códigos de issue (p. ej. de configuración), sin valores. */
  readonly issues?: readonly string[];
}

const ALLOWED_KEYS = ['op', 'route', 'status', 'kind', 'reason', 'requestId', 'ms', 'instancePath', 'keyword', 'issues'] as const;

/** Copia solo las claves permitidas y con tipos primitivos esperados. */
export function sanitizeLogFields(fields: LogFields): LogFields {
  const out: Record<string, unknown> = {};
  for (const key of ALLOWED_KEYS) {
    const value = fields[key];
    if (value === undefined) continue;
    if (key === 'issues') {
      if (Array.isArray(value)) out.issues = value.filter((v): v is string => typeof v === 'string').slice(0, 20);
      continue;
    }
    if (typeof value === 'string') out[key] = value.slice(0, 120);
    else if (typeof value === 'number' && Number.isFinite(value)) out[key] = value;
    else if (value === null) out[key] = null;
  }
  return out as LogFields;
}

function emitEnabled(): boolean {
  return import.meta.env.DEV && import.meta.env.MODE !== 'test';
}

export const log = {
  warn(fields: LogFields): void {
    if (!emitEnabled()) return;
    console.warn('[brujula]', sanitizeLogFields(fields));
  },
  error(fields: LogFields): void {
    if (!emitEnabled()) return;
    console.error('[brujula]', sanitizeLogFields(fields));
  },
};
