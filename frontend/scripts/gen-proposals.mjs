#!/usr/bin/env node
// Genera el validador Ajv standalone de las operaciones PROPUESTAS del frontend (fuera de C3,
// DEC-039). Mismo runtime y mismas guardas que scripts/gen-contract.mjs (DEC-031): sin require,
// eval ni new Function. "Agregar información" reutiliza FamiliaDetailEnvelope de C3 como respuesta
// (solo se compila su request); "alcance territorial" (DEC-072) compila su envelope de respuesta.
// Rutas con fileURLToPath: la ruta del repo tiene espacios.
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { _ } from 'ajv';
import Ajv2020 from 'ajv/dist/2020.js';
import standaloneCode from 'ajv/dist/standalone/index.js';
import * as runtime from '../src/api/contract/runtime.js';

const proposalsDir = fileURLToPath(new URL('../src/api/proposals/', import.meta.url));
const outDir = path.join(proposalsDir, 'generated');
/** Validador → [schema en src/api/proposals/, tipo exportado por src/api/proposals/types.ts]. */
const SCHEMAS = {
  validateAddFamilyInfoRequestV1: ['AddFamilyInfoRequestV1.schema.json', 'AddFamilyInfoRequestV1'],
  validateCatalogScopeEnvelopeV1: ['CatalogScopeEnvelopeV1.schema.json', 'CatalogScopeEnvelopeV1'],
};

function fail(message) {
  console.error(`gen:proposals FALLA: ${message}`);
  process.exit(1);
}

const ajv = new Ajv2020({
  strict: true,
  strictTypes: false,
  allowUnionTypes: true,
  code: { source: true, esm: true, formats: _`require("../../contract/runtime.js").formats` },
  formats: runtime.formats,
});

const mapping = {};
const hashes = {};
for (const [name, [file]] of Object.entries(SCHEMAS)) {
  const text = readFileSync(path.join(proposalsDir, file), 'utf8').replace(/\r\n/g, '\n');
  const schema = JSON.parse(text);
  if (typeof schema.$id !== 'string' || schema.$id === '') fail(`schema sin $id: ${file}`);
  ajv.addSchema(schema);
  mapping[name] = schema.$id;
  hashes[file] = createHash('sha256').update(text, 'utf8').digest('hex');
}

let code = standaloneCode(ajv, mapping);
code = code
  .replaceAll('require("ajv/dist/runtime/equal").default', '__rt.equal')
  .replaceAll('require("ajv/dist/runtime/ucs2length").default', '__rt.ucs2length')
  .replaceAll('require("../../contract/runtime.js")', '__rt');
code = `// GENERADO por scripts/gen-proposals.mjs (propuestas fuera de C3, DEC-039). No editar.\nimport * as __rt from "../../contract/runtime.js";\n${code}`;
for (const forbidden of ['require(', 'eval(', 'new Function']) {
  if (code.includes(forbidden)) fail(`validators.gen.js contiene ${forbidden}`);
}

const entries = Object.entries(SCHEMAS);
const dts = [
  '// GENERADO por scripts/gen-proposals.mjs. No editar.',
  "import type { ValidateFn } from '../../generated/validators.gen.js';",
  `import type { ${entries.map(([, [, type]]) => type).join(', ')} } from '../types';`,
  '',
  ...entries.map(([name, [, type]]) => `export declare const ${name}: ValidateFn<${type}>;`),
  '',
].join('\n');

mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, 'validators.gen.js'), code.replace(/\r\n/g, '\n'), 'utf8');
writeFileSync(path.join(outDir, 'validators.gen.d.ts'), dts, 'utf8');
writeFileSync(
  path.join(outDir, 'proposals.meta.json'),
  `${JSON.stringify({ generator: 'scripts/gen-proposals.mjs', files: hashes, validators: mapping }, null, 2)}\n`,
  'utf8',
);
console.log(`gen:proposals OK · ${Object.keys(mapping).length} validador(es)`);
