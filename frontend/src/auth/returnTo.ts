// `returnTo` del login (design.md §14.1): path del mismo origen, que empieza con `/` y no con
// `//` ni `/\`, ≤ 512 caracteres y que calza con una ruta conocida de §9; si no, `/`.
// Solo conserva la query validada (`?jardin`, `?orden`); nunca datos de formulario.
import { isValidId } from '../domain/ids';

const MAX_LENGTH = 512;
const SENTINEL_ORIGIN = 'https://brujula.invalid';
const ID = '[A-Z0-9][A-Z0-9_-]{0,79}';
const KNOWN_ROUTES: readonly RegExp[] = [
  /^\/$/,
  new RegExp(`^/familias/${ID}$`),
  new RegExp(`^/familias/${ID}/(guion|mensaje|conversacion)$`),
  /^\/familia-nueva$/,
  /^\/avance$/,
  /^\/asistente$/,
];
const ORDERS = new Set(['prioridad', 'urgencia', 'beneficio']);

export function sanitizeReturnTo(raw: unknown): string {
  if (typeof raw !== 'string' || raw.length === 0 || raw.length > MAX_LENGTH) return '/';
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return '/';
  // Barras invertidas, espacios y caracteres de control: el navegador los normaliza de formas
  // que podrían cambiar el destino.
  if (/[\\\s]/.test(raw) || [...raw].some((ch) => ch.charCodeAt(0) < 0x20 || ch.charCodeAt(0) === 0x7f)) return '/';
  let url: URL;
  try {
    url = new URL(raw, SENTINEL_ORIGIN);
  } catch {
    return '/';
  }
  if (url.origin !== SENTINEL_ORIGIN) return '/';
  if (!KNOWN_ROUTES.some((re) => re.test(url.pathname))) return '/';
  const query = new URLSearchParams();
  const jardin = url.searchParams.get('jardin');
  if (jardin !== null && isValidId(jardin)) query.set('jardin', jardin);
  const orden = url.searchParams.get('orden');
  if (orden !== null && ORDERS.has(orden)) query.set('orden', orden);
  const search = query.toString();
  return search === '' ? url.pathname : `${url.pathname}?${search}`;
}
