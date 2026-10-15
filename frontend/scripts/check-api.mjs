// npm run check:api [-- <url>] — Verifica que una API C3 LOCAL (loopback) responda los GET de C3 con
// envelopes válidos según los validadores Ajv generados (src/api/generated/validators.gen.js).
// Solo GET (sin POST), sin tokens ni credenciales. Imprime OK/FAIL por ruta normalizada; nunca
// vuelca bodies ni valores: ante FAIL solo status, media type o instancePath + keyword del schema.
// URL: argumento, o BRUJULA_API_CHECK_URL, o http://127.0.0.1:8000/api/v1. Sale con 1 si algo falla.
import { pathToFileURL } from 'node:url';
import {
  validateFamiliaContextEnvelope,
  validateFamiliaDetailEnvelope,
  validateFamiliaListEnvelope,
  validateJardinListEnvelope,
  validateKpiEnvelope,
  validateOpportunityListEnvelope,
} from '../src/api/generated/validators.gen.js';

export const DEFAULT_API_CHECK_URL = 'http://127.0.0.1:8000/api/v1';
const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
const TIMEOUT_MS = 10_000;

/** Base absoluta loopback terminada en /api/v1 (sin barra final) o null. */
export function resolveCheckBaseUrl(raw) {
  try {
    const url = new URL(raw);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    if (!LOOPBACK_HOSTS.has(url.hostname) || url.username !== '' || url.password !== '' || url.search !== '' || url.hash !== '') return null;
    const pathname = url.pathname.replace(/\/$/, '');
    if (!pathname.endsWith('/api/v1')) return null;
    return `${url.origin}${pathname}`;
  } catch {
    return null;
  }
}

async function getEnvelope(fetchImpl, baseUrl, path, query, validate) {
  const url = new URL(`${baseUrl}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) url.searchParams.set(key, value);
  let response;
  try {
    response = await fetchImpl(url.href, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      redirect: 'manual',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (error) {
    const reason = error?.name === 'TimeoutError' ? 'timeout' : 'red';
    return { ok: false, status: null, detail: reason };
  }
  const status = response.status;
  const mediaType = (response.headers.get('content-type') ?? '').split(';')[0].trim().toLowerCase();
  if (status !== 200) {
    await response.body?.cancel();
    return { ok: false, status, detail: 'status inesperado' };
  }
  if (mediaType !== 'application/json') {
    await response.body?.cancel();
    return { ok: false, status, detail: 'content-type no es application/json' };
  }
  let body;
  try {
    body = await response.json();
  } catch {
    return { ok: false, status, detail: 'JSON inválido' };
  }
  if (!validate(body)) {
    const first = validate.errors?.[0];
    return { ok: false, status, detail: `schema ${first?.instancePath || '/'} ${first?.keyword ?? ''}`.trim() };
  }
  return { ok: true, status, body };
}

/**
 * Recorre los GET de C3 encadenando IDs reales de la respuesta anterior (primer jardín y primera
 * familia). Devuelve { ok, results } y escribe una línea por ruta con `out`.
 */
export async function runApiCheck({ baseUrl, fetchImpl = (...args) => globalThis.fetch(...args), out = (line) => console.log(line) }) {
  const results = [];
  const record = (route, result) => {
    results.push({ route, ok: result.ok, status: result.status, detail: result.detail ?? null });
    const status = result.status === null || result.status === undefined ? '---' : String(result.status);
    out(`${result.ok ? 'OK  ' : 'FAIL'} ${status} GET ${route}${result.ok ? '' : ` — ${result.detail}`}`);
    return result;
  };
  const skip = (route, why) => {
    results.push({ route, ok: false, status: null, detail: why });
    out(`FAIL --- GET ${route} — omitida: ${why}`);
  };

  const jardines = record('/jardines?limit=100', await getEnvelope(fetchImpl, baseUrl, '/jardines', { limit: '100' }, validateJardinListEnvelope));
  const gardenId = jardines.ok ? jardines.body.items[0]?.garden_id : undefined;

  let familyId;
  if (gardenId === undefined) {
    skip('/jardines/{id}/familias', jardines.ok ? 'sin jardines' : 'falló /jardines');
  } else {
    const familias = record(
      '/jardines/{id}/familias',
      await getEnvelope(fetchImpl, baseUrl, `/jardines/${encodeURIComponent(gardenId)}/familias`, {}, validateFamiliaListEnvelope),
    );
    familyId = familias.ok ? familias.body.items[0]?.family_id : undefined;
  }

  const familyRoutes = [
    ['/familias/{id}', '', {}, validateFamiliaDetailEnvelope],
    ['/familias/{id}/contexto', '/contexto', {}, validateFamiliaContextEnvelope],
    ['/familias/{id}/oportunidades?orden=prioridad', '/oportunidades', { orden: 'prioridad' }, validateOpportunityListEnvelope],
    ['/familias/{id}/oportunidades?orden=urgencia', '/oportunidades', { orden: 'urgencia' }, validateOpportunityListEnvelope],
    ['/familias/{id}/oportunidades?orden=beneficio', '/oportunidades', { orden: 'beneficio' }, validateOpportunityListEnvelope],
  ];
  for (const [route, suffix, query, validate] of familyRoutes) {
    if (familyId === undefined) skip(route, 'sin familia de referencia');
    else record(route, await getEnvelope(fetchImpl, baseUrl, `/familias/${encodeURIComponent(familyId)}${suffix}`, query, validate));
  }

  record('/kpi?nivel=nacional', await getEnvelope(fetchImpl, baseUrl, '/kpi', { nivel: 'nacional' }, validateKpiEnvelope));
  if (gardenId === undefined) skip('/kpi?nivel=jardin&id={id}', 'sin jardín de referencia');
  else record('/kpi?nivel=jardin&id={id}', await getEnvelope(fetchImpl, baseUrl, '/kpi', { nivel: 'jardin', id: gardenId }, validateKpiEnvelope));

  const ok = results.every((r) => r.ok);
  out(ok ? `Resultado: ${results.length}/${results.length} rutas OK` : `Resultado: ${results.filter((r) => r.ok).length}/${results.length} rutas OK`);
  return { ok, results };
}

async function main() {
  const raw = process.argv[2] ?? process.env.BRUJULA_API_CHECK_URL ?? DEFAULT_API_CHECK_URL;
  const baseUrl = resolveCheckBaseUrl(raw);
  if (baseUrl === null) {
    console.error('check:api: la URL debe ser loopback (localhost/127.0.0.1/[::1]) y terminar en /api/v1.');
    process.exit(2);
  }
  console.log(`check:api contra ${baseUrl} (C3 GET, validadores Ajv generados)`);
  const { ok } = await runApiCheck({ baseUrl });
  process.exit(ok ? 0 : 1);
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  void main();
}
