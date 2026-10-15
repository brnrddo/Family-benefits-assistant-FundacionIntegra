// Único filtro de URLs para enlaces externos (design.md §11.3, FE-009). Solo `SourceCitation.url`
// llega aquí; el resultado es el href normalizado o null (se muestra el source_id como texto).
export function toSafeHttpsUrl(raw: unknown): string | null {
  if (typeof raw !== 'string' || raw.length === 0 || raw.length > 2048) return null;
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  if (url.protocol !== 'https:') return null;
  if (url.hostname === '') return null;
  if (url.username !== '' || url.password !== '') return null;
  return url.href;
}
