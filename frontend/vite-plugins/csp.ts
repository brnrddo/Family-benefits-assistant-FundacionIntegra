// Meta CSP solo en build (design.md §15). Sin scripts ni estilos inline.
// `frame-ancestors` no es válido en <meta>; va en los headers de hosting (§14, PREG-033).
import type { Plugin } from 'vite';

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

function parseUrl(value: string | undefined): URL | null {
  if (value === undefined || value === '') return null;
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

export function isLoopbackHttpUrl(value: string): boolean {
  const url = parseUrl(value);
  return url !== null && (url.protocol === 'http:' || url.protocol === 'https:') && LOOPBACK_HOSTS.has(url.hostname);
}

/** Origen seguro para CSP: https, o http solo en loopback; sin credenciales. */
export function safeOrigin(value: string | undefined): string | null {
  const url = parseUrl(value);
  if (url === null || url.username !== '' || url.password !== '') return null;
  if (url.protocol === 'https:' || (url.protocol === 'http:' && LOOPBACK_HOSTS.has(url.hostname))) return url.origin;
  return null;
}

export interface CspOptions {
  readonly apiBaseUrl?: string;
  readonly cognitoAuthority?: string;
  readonly cognitoDomain?: string;
}

export function buildCsp(options: CspOptions): string {
  const api = safeOrigin(options.apiBaseUrl);
  const authority = safeOrigin(options.cognitoAuthority);
  const domain = safeOrigin(options.cognitoDomain);
  const unique = (values: (string | null)[]) => [...new Set(values.filter((v): v is string => v !== null))];
  const connect = unique(["'self'", api, authority, domain]);
  const formAction = unique(["'self'", domain]);
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src ${connect.join(' ')}`,
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    `form-action ${formAction.join(' ')}`,
  ].join('; ');
}

export function cspPlugin(options: CspOptions): Plugin {
  return {
    name: 'brujula-csp',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler() {
        return [
          {
            tag: 'meta',
            attrs: { 'http-equiv': 'Content-Security-Policy', content: buildCsp(options) },
            injectTo: 'head-prepend',
          },
        ];
      },
    },
  };
}
