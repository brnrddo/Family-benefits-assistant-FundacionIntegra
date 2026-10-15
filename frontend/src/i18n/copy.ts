// Copy en runtime (§7.3). `t()` devuelve SIEMPRE un string que se renderiza como texto React;
// los números, montos y fechas se formatean antes con domain/format.ts.
import { copyValues } from 'virtual:brujula-content';
import { COPY_CATALOG, type CopyKey, type CopyParams } from './catalog';

type TArgs<K extends CopyKey> = CopyParams<K> extends undefined ? [] : [params: CopyParams<K>];

/** Claves sin placeholders: las que pueden venir de un mapeo enum → clave (domain/presentation.ts). */
export type PlainCopyKey = { [K in CopyKey]: CopyParams<K> extends undefined ? K : never }[CopyKey];

const PLACEHOLDER_RE = /\{([a-z0-9_]+)\}/g;

export function t<K extends CopyKey>(key: K, ...args: TArgs<K>): string {
  const template = copyValues[key] ?? key;
  const params = args[0] as Readonly<Record<string, string | number>> | undefined;
  if (params === undefined) return template;
  const allowed: readonly string[] = COPY_CATALOG[key].placeholders;
  return template.replace(PLACEHOLDER_RE, (match, name: string) =>
    allowed.includes(name) && Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match,
  );
}

/**
 * Nombre visible de un beneficio: `simple_title` de C3 si existe; si no, la clave opcional
 * `benefit.<id en minúsculas>.name`; si tampoco existe, el propio ID.
 */
export function benefitName(benefitId: string, simpleTitle?: string | null): string {
  if (typeof simpleTitle === 'string' && simpleTitle !== '') return simpleTitle;
  return copyValues[`benefit.${benefitId.toLowerCase()}.name`] ?? benefitId;
}
