// Variantes INVÁLIDAS derivadas por clonación de fixtures válidos (plan: decisiones de
// implementación). Así todo fixtures/*.json es válido para su operación y los casos adversariales
// de contrato (§11.4) no necesitan archivos propios. No definen hogares nuevos.
import { payloadOf } from './fixtureStore';

type Json = Record<string, unknown>;

function mensaje(): Json & { content: { printable_card: { sections: Json[] } & Json } } {
  return payloadOf('createMensaje.bedrock');
}

/** Cita `http://` (C3 exige `^https://`). */
export function messageWithHttpCitation(): unknown {
  const body = mensaje();
  const sources = body.content.printable_card.sections[0]?.sources as { url: string }[];
  sources[0] = { ...sources[0], url: 'http://fuentes.brujula-demo.example/ben-001' } as { url: string };
  return body;
}

/** Cita `javascript:`. */
export function messageWithJavascriptCitation(): unknown {
  const body = mensaje();
  const sources = body.content.printable_card.sections[0]?.sources as { url: string }[];
  sources[0] = { ...sources[0], url: 'javascript:alert(1)' } as { url: string };
  return body;
}

/** Propiedad extra `html` en la tarjeta. */
export function messageWithHtmlProperty(): unknown {
  const body = mensaje();
  (body.content.printable_card as Json).html = '<b>x</b>';
  return body;
}

/** Más de 3 secciones. */
export function messageWithFourSections(): unknown {
  const body = mensaje();
  const sections = body.content.printable_card.sections;
  sections.push(structuredClone(sections[0] as Json));
  return body;
}

/** `format_version` distinto de CARD_V1. */
export function messageWithWrongFormatVersion(): unknown {
  const body = mensaje();
  (body.content.printable_card as Json).format_version = 'CARD_V2';
  return body;
}

/** Oportunidad con `result: SI` y `level: null` (oneOf de C3 lo prohíbe). */
export function opportunitiesWithSiAndNullLevel(): unknown {
  const body = payloadOf<{ items: Json[] }>('listOportunidades.FAM-SIM-E3-00001.prioridad');
  (body.items[0] as Json).level = null;
  return body;
}

/** Propiedad extra en un envelope cerrado. */
export function jardinesWithExtraProperty(): unknown {
  const body = payloadOf<Json>('listJardines');
  body.debug = true;
  return body;
}

/** Enum inválido en un FamilySummary. */
export function familiasWithInvalidEnum(): unknown {
  const body = payloadOf<{ items: Json[] }>('listFamiliasByJardin.JAR-SIM-E3-00001.p1');
  (body.items[0] as Json).traffic_light = 'ROJO';
  return body;
}
