#!/usr/bin/env node
// Presupuesto de bundle (design.md §10.5 V-15, NIT 16) sobre dist/ ya construido.
// JS inicial = <script type="module" src> de dist/index.html + todos sus <link rel="modulepreload">.
// JS total = dist/assets/*.js. CSS = dist/assets/*.css. gzip nivel 9 con node:zlib.
// Un build sin mocks no puede contener msw. Imprime una tabla y sale con 1 si algo se excede.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const KIB = 1024;
const LIMITS = { initialJs: 200 * KIB, totalJs: 350 * KIB, css: 30 * KIB };
const distDir = fileURLToPath(new URL('../dist/', import.meta.url));
const assetsDir = path.join(distDir, 'assets');

function fail(message) {
  console.error(`check:budget FALLA: ${message}`);
  process.exit(1);
}

if (!existsSync(path.join(distDir, 'index.html'))) fail('no existe dist/index.html (ejecute npm run build)');

const gz = (file) => gzipSync(readFileSync(file), { level: 9 }).byteLength;
const attr = (tag, name) => new RegExp(`\\s${name}\\s*=\\s*"([^"]*)"`, 'i').exec(tag)?.[1] ?? null;
const toDistFile = (url) => path.join(distDir, ...url.replace(/^\//, '').split('/'));

const html = readFileSync(path.join(distDir, 'index.html'), 'utf8');
const initial = new Set();
for (const tag of html.match(/<script\b[^>]*>/gi) ?? []) {
  const src = attr(tag, 'src');
  if (attr(tag, 'type') === 'module' && src !== null) initial.add(src);
}
for (const tag of html.match(/<link\b[^>]*>/gi) ?? []) {
  const href = attr(tag, 'href');
  if (attr(tag, 'rel') === 'modulepreload' && href !== null) initial.add(href);
}
if (initial.size === 0) fail('dist/index.html no declara un <script type="module">');
const initialFiles = [...initial].map(toDistFile);
for (const file of initialFiles) if (!existsSync(file)) fail(`asset inicial inexistente: ${path.basename(file)}`);

const assets = existsSync(assetsDir) ? readdirSync(assetsDir) : [];
const jsFiles = assets.filter((f) => f.endsWith('.js')).map((f) => path.join(assetsDir, f));
const cssFiles = assets.filter((f) => f.endsWith('.css')).map((f) => path.join(assetsDir, f));

const sum = (files) => files.reduce((total, file) => total + gz(file), 0);
const rows = [
  ['JS inicial (entry + modulepreload)', sum(initialFiles), LIMITS.initialJs, initialFiles.length],
  ['JS total (dist/assets/*.js)', sum(jsFiles), LIMITS.totalJs, jsFiles.length],
  ['CSS (dist/assets/*.css)', sum(cssFiles), LIMITS.css, cssFiles.length],
];

// build-info.json lo emite vite-plugins/brujula-content.ts; sin él se asume "sin mocks" (falla cerrada).
let mocks = false;
const infoFile = path.join(distDir, 'build-info.json');
if (existsSync(infoFile)) mocks = JSON.parse(readFileSync(infoFile, 'utf8')).mocks === true;
// Firmas de msw / @mswjs/interceptors que sobreviven a la minificación.
const MSW_SIGNATURES = ['[MSW]', 'mswjs', 'onUnhandledFrame', 'X-Msw'];
const mswFiles = jsFiles.filter((file) => {
  const text = readFileSync(file, 'utf8');
  return MSW_SIGNATURES.some((signature) => text.includes(signature));
});

const kb = (bytes) => `${(bytes / KIB).toFixed(1)} KB`;
console.log('check:budget (gzip nivel 9; 1 KB = 1024 bytes)');
console.log('| Medida | Archivos | gzip | Límite | Estado |');
console.log('|---|---:|---:|---:|---|');
let exceeded = false;
for (const [label, bytes, limit, count] of rows) {
  const ok = bytes <= limit;
  exceeded ||= !ok;
  console.log(`| ${label} | ${count} | ${kb(bytes)} | ${kb(limit)} | ${ok ? 'OK' : 'EXCEDIDO'} |`);
}
const mswOk = mocks || mswFiles.length === 0;
console.log(`| msw en build ${mocks ? 'CON' : 'SIN'} mocks | ${mswFiles.length} | — | ${mocks ? 'permitido' : '0 archivos'} | ${mswOk ? 'OK' : 'EXCEDIDO'} |`);
if (!mswOk) {
  console.error(`msw presente en un build sin mocks: ${mswFiles.map((f) => path.basename(f)).join(', ')}`);
  exceeded = true;
}
if (exceeded) process.exit(1);
console.log('check:budget OK');
