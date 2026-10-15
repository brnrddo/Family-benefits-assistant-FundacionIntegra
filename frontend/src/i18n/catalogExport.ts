// Forma de frontend/i18n-catalog.json (§7.1): {meta, keys: [{key, placeholders: [{name, tipo}], uso}]}.
// La usan scripts/export-i18n-catalog.mjs y la prueba que exige igualdad con el JSON versionado.
// Import con extensión .ts: Node lo carga sin bundler (type stripping).
import { CATALOG_META, COPY_CATALOG } from './catalog.ts';

export interface CatalogExport {
  readonly meta: typeof CATALOG_META;
  readonly keys: readonly {
    readonly key: string;
    readonly placeholders: readonly { readonly name: string; readonly tipo: string }[];
    readonly uso: string;
  }[];
}

export function buildCatalogExport(): CatalogExport {
  return {
    meta: CATALOG_META,
    keys: Object.entries(COPY_CATALOG).map(([key, entry]) => {
      const tipo = entry.tipo as Readonly<Record<string, string>>;
      return {
        key,
        placeholders: entry.placeholders.map((name: string) => ({ name, tipo: tipo[name] ?? 'string' })),
        uso: entry.uso,
      };
    }),
  };
}
