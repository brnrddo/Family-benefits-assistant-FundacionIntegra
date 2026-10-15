#!/usr/bin/env node
// Genera tipos, validadores Ajv standalone y metadatos desde C3 (design.md §6.1, DEC-031).
// Lee C3 y sus refs externos SIN escribirlos. Falla cerrado (exit 1) ante cualquier
// ref sin resolver, $id faltante o duplicado, o código generado con require/eval/new Function.
// Rutas con pathToFileURL/fileURLToPath: la ruta del repo tiene espacios.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { _ } from 'ajv';
import Ajv2020 from 'ajv/dist/2020.js';
import standaloneCode from 'ajv/dist/standalone/index.js';
import openapiTS, { astToString } from 'openapi-typescript';
import { parse as parseYaml } from 'yaml';
import * as runtime from '../src/api/contract/runtime.js';

const frontendDir = fileURLToPath(new URL('..', import.meta.url));
const c3Path = path.resolve(
  frontendDir,
  process.env.BRUJULA_C3_PATH ?? '../.kiro/specs/_shared/contracts/C3-api.openapi.yaml',
);
const outDir = fileURLToPath(new URL('../src/api/generated/', import.meta.url));
const C3_COMPONENTS_ID = 'urn:brujula:c3:components';

class GenError extends Error {}

function fail(message) {
  throw new GenError(message);
}

/** Texto UTF-8 con CRLF normalizado a LF (core.autocrlf=true en Windows). */
function readNormalized(fileUrl) {
  const filePath = fileURLToPath(fileUrl);
  if (!existsSync(filePath)) fail(`archivo referenciado no existe: ${path.basename(filePath)}`);
  return readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n');
}

function sha256(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

const isPlainObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

/** Recorre el árbol y llama visit(holder) por cada objeto con `$ref` string. */
function walkRefs(node, visit) {
  if (Array.isArray(node)) {
    for (const item of node) walkRefs(item, visit);
    return;
  }
  if (!isPlainObject(node)) return;
  if (typeof node.$ref === 'string') visit(node);
  for (const value of Object.values(node)) walkRefs(value, visit);
}

const isLocalOrUrn = (ref) => ref.startsWith('#') || ref.startsWith('urn:');

function splitRef(ref) {
  const index = ref.indexOf('#');
  return index === -1 ? [ref, ''] : [ref.slice(0, index), ref.slice(index + 1)];
}

async function main() {
  const c3Url = pathToFileURL(c3Path);
  const c3Dir = new URL('.', c3Url);
  const c3Text = readNormalized(c3Url);
  const c3 = parseYaml(c3Text);
  if (!isPlainObject(c3) || !isPlainObject(c3.components) || !isPlainObject(c3.components.schemas)) {
    fail('C3 sin components.schemas');
  }

  // 1) Cargar externos de forma recursiva (paths + components y cada archivo cargado).
  /** @type {Map<string, {id: string, json: object, text: string}>} href -> archivo */
  const files = new Map();
  /** @type {Map<string, string>} $id -> href */
  const ids = new Map();
  const pending = [{ node: c3, baseHref: c3Url.href }];
  while (pending.length > 0) {
    const { node, baseHref } = pending.shift();
    walkRefs(node, (holder) => {
      const ref = holder.$ref;
      if (isLocalOrUrn(ref)) return;
      const [filePart] = splitRef(ref);
      const target = new URL(filePart, baseHref);
      if (files.has(target.href)) return;
      const text = readNormalized(target);
      let json;
      try {
        json = JSON.parse(text);
      } catch {
        fail(`JSON inválido: ${path.basename(fileURLToPath(target))}`);
      }
      if (!isPlainObject(json) || typeof json.$id !== 'string' || json.$id === '') {
        fail(`schema sin $id: ${path.basename(fileURLToPath(target))}`);
      }
      if (ids.has(json.$id) || json.$id === C3_COMPONENTS_ID) fail(`$id duplicado: ${json.$id}`);
      ids.set(json.$id, target.href);
      files.set(target.href, { id: json.$id, json, text });
      pending.push({ node: json, baseHref: target.href });
    });
  }

  // 2) Reescribir refs a $id (+ fragmento). Las #/$defs/... de cada archivo quedan intactas.
  const rewrite = (node, baseHref, isC3) => {
    const copy = structuredClone(node);
    walkRefs(copy, (holder) => {
      const ref = holder.$ref;
      if (ref.startsWith('urn:')) return;
      if (ref.startsWith('#')) {
        if (isC3) {
          const match = /^#\/components\/schemas\/([^/]+)$/.exec(ref);
          if (match === null) fail(`ref interna de C3 no soportada: ${ref}`);
          holder.$ref = `${C3_COMPONENTS_ID}#/$defs/${match[1]}`;
        }
        return;
      }
      const [filePart, fragment] = splitRef(ref);
      const target = new URL(filePart, baseHref).href;
      const file = files.get(target);
      if (file === undefined) fail(`ref sin resolver: ${ref}`);
      holder.$ref = fragment === '' ? file.id : `${file.id}#${fragment}`;
    });
    return copy;
  };

  const c3Components = {
    $id: C3_COMPONENTS_ID,
    $defs: rewrite(c3.components.schemas, c3Url.href, true),
  };
  const externals = [...files.entries()].map(([href, file]) => rewrite(file.json, href, false));

  // 3) Comprobar antes de compilar: toda ref no local debe resolver a un $id registrado.
  const registered = new Set([C3_COMPONENTS_ID, ...ids.keys()]);
  for (const schema of [c3Components, ...externals]) {
    walkRefs(schema, (holder) => {
      const ref = holder.$ref;
      if (ref.startsWith('#')) return;
      const [base] = splitRef(ref);
      if (!registered.has(base)) fail(`ref sin $id registrado: ${ref}`);
    });
  }

  // 4) Operaciones C3 (12) y su status/envelope de éxito.
  const operations = {};
  const responses = c3.components.responses ?? {};
  const schemaNameFromRef = (ref) => /^#\/components\/schemas\/([^/]+)$/.exec(ref)?.[1];
  for (const [routePath, item] of Object.entries(c3.paths ?? {})) {
    for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
      const op = item?.[method];
      if (!isPlainObject(op)) continue;
      const successStatus = Object.keys(op.responses ?? {}).find((status) => /^2\d\d$/.test(status));
      if (successStatus === undefined) fail(`operación sin 2xx: ${op.operationId}`);
      const responseRef = op.responses[successStatus].$ref;
      const responseName = /^#\/components\/responses\/([^/]+)$/.exec(responseRef ?? '')?.[1];
      const response = responseName === undefined ? undefined : responses[responseName];
      const envelope = schemaNameFromRef(response?.content?.['application/json']?.schema?.$ref ?? '');
      if (envelope === undefined) fail(`envelope de éxito no encontrado: ${op.operationId}`);
      const bodyRef = op.requestBody?.content?.['application/json']?.schema?.$ref;
      let request = null;
      if (typeof bodyRef === 'string') {
        request = schemaNameFromRef(bodyRef) ?? files.get(new URL(splitRef(bodyRef)[0], c3Url).href)?.json.title;
        if (request === undefined) fail(`request sin schema: ${op.operationId}`);
      }
      operations[op.operationId] = {
        method: method.toUpperCase(),
        path: routePath,
        expectedStatus: Number(successStatus),
        response: envelope,
        request,
      };
    }
  }
  const operationIds = Object.keys(operations).sort();
  if (operationIds.length !== 12) fail(`se esperaban 12 operationId y hay ${operationIds.length}`);

  // 5) Disclaimer único (const común a todos los envelopes).
  const disclaimers = new Set();
  const collectDisclaimers = (node) => {
    if (Array.isArray(node)) return node.forEach(collectDisclaimers);
    if (!isPlainObject(node)) return;
    if (isPlainObject(node.properties) && isPlainObject(node.properties.disclaimer)) {
      const value = node.properties.disclaimer.const;
      if (typeof value !== 'string') fail('disclaimer sin const');
      disclaimers.add(value);
    }
    Object.values(node).forEach(collectDisclaimers);
  };
  collectDisclaimers(c3.components.schemas);
  if (disclaimers.size !== 1) fail(`se esperaba un disclaimer único y hay ${disclaimers.size}`);
  const [disclaimer] = [...disclaimers];

  // 6) Validadores: 12 envelopes + ErrorResponse + 5 cuerpos de request.
  const externalIdByTitle = new Map([...files.values()].map((file) => [file.json.title, file.id]));
  const errorId = externalIdByTitle.get('ErrorResponse');
  if (errorId === undefined) fail('ErrorResponse no cargado');
  const mapping = {};
  const typeExpr = {};
  for (const id of operationIds) {
    const { response, request } = operations[id];
    mapping[`validate${response}`] = `${C3_COMPONENTS_ID}#/$defs/${response}`;
    typeExpr[`validate${response}`] = `components['schemas']['${response}']`;
    if (request !== null) {
      if (c3.components.schemas[request] !== undefined) {
        mapping[`validate${request}`] = `${C3_COMPONENTS_ID}#/$defs/${request}`;
        typeExpr[`validate${request}`] = `components['schemas']['${request}']`;
      } else {
        mapping[`validate${request}`] = externalIdByTitle.get(request);
        typeExpr[`validate${request}`] = `NonNullable<operations['${id}']['requestBody']>['content']['application/json']`;
      }
    }
  }
  mapping.validateErrorResponse = errorId;
  typeExpr.validateErrorResponse = `components['responses']['Error400']['content']['application/json']`;
  const validatorNames = Object.keys(mapping).sort();
  if (validatorNames.length !== 18) fail(`se esperaban 18 validadores y hay ${validatorNames.length}`);
  const sortedMapping = Object.fromEntries(validatorNames.map((name) => [name, mapping[name]]));

  const ajv = new Ajv2020({
    strict: true,
    strictTypes: false,
    allowUnionTypes: true,
    code: { source: true, esm: true, formats: _`require("../contract/runtime.js").formats` },
    formats: runtime.formats,
  });
  ajv.addSchema(c3Components);
  for (const schema of externals) ajv.addSchema(schema);
  let code = standaloneCode(ajv, sortedMapping);
  code = code
    .replaceAll('require("ajv/dist/runtime/equal").default', '__rt.equal')
    .replaceAll('require("ajv/dist/runtime/ucs2length").default', '__rt.ucs2length')
    .replaceAll('require("../contract/runtime.js")', '__rt');
  code = `// GENERADO por scripts/gen-contract.mjs desde C3 v${c3.info?.version}. No editar.\nimport * as __rt from "../contract/runtime.js";\n${code}`;
  for (const forbidden of ['require(', 'eval(', 'new Function']) {
    if (code.includes(forbidden)) fail(`validators.gen.js contiene ${forbidden}`);
  }

  // 7) Tipos con openapi-typescript (API programática).
  const ast = await openapiTS(c3Url);
  const dts = astToString(ast);

  const validatorsDts = [
    '// GENERADO por scripts/gen-contract.mjs. No editar.',
    "import type { components, operations } from './c3';",
    '',
    'export type ValidateFn<T> = ((data: unknown) => data is T) & {',
    '  errors?: { instancePath: string; keyword: string }[] | null;',
    '};',
    '',
    ...validatorNames.map((name) => `export declare const ${name}: ValidateFn<${typeExpr[name]}>;`),
    '',
  ].join('\n');

  // 8) Metadatos deterministas (sin timestamps); hashes sobre texto con LF.
  const relative = (href) => path.relative(fileURLToPath(c3Dir), fileURLToPath(href)).split(path.sep).join('/');
  const hashes = { [relative(c3Url.href)]: sha256(c3Text) };
  for (const [href, file] of files) hashes[relative(href)] = sha256(file.text);
  const meta = {
    generator: 'scripts/gen-contract.mjs',
    info_version: c3.info?.version,
    disclaimer,
    files: Object.fromEntries(Object.keys(hashes).sort().map((key) => [key, hashes[key]])),
    operations: Object.fromEntries(operationIds.map((id) => [id, operations[id]])),
    validators: sortedMapping,
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(path.join(outDir, 'c3.d.ts'), dts.replace(/\r\n/g, '\n'), 'utf8');
  writeFileSync(path.join(outDir, 'validators.gen.js'), code.replace(/\r\n/g, '\n'), 'utf8');
  writeFileSync(path.join(outDir, 'validators.gen.d.ts'), validatorsDts, 'utf8');
  writeFileSync(path.join(outDir, 'c3.meta.json'), `${JSON.stringify(meta, null, 2)}\n`, 'utf8');
  console.log(`gen:contract OK · C3 v${meta.info_version} · ${operationIds.length} operaciones · ${validatorNames.length} validadores`);
}

main().catch((error) => {
  console.error(error instanceof GenError ? `gen:contract FALLA: ${error.message}` : error);
  process.exit(1);
});
