#!/usr/bin/env node
// Exporta src/i18n/catalog.ts → frontend/i18n-catalog.json (handoff a Rol 4, §7.1).
// Node ≥ 22.18 importa .ts con sintaxis borrable sin flags; catalog.ts no usa enums.
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { buildCatalogExport } from '../src/i18n/catalogExport.ts';

const target = fileURLToPath(new URL('../i18n-catalog.json', import.meta.url));
const json = `${JSON.stringify(buildCatalogExport(), null, 2)}\n`;
writeFileSync(target, json, 'utf8');
const { keys } = JSON.parse(json);
console.log(`export:i18n-catalog OK · ${keys.length} claves → i18n-catalog.json`);
