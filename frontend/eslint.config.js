// ESLint 9 (flat config). Reglas de seguridad de §11.2 y fronteras de FE-003 (§4.1).
import js from '@eslint/js';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

/** Parsers/renderers de HTML o Markdown prohibidos en todo el frontend (FE-009). */
const FORBIDDEN_HTML_PACKAGES = [
  'html-react-parser',
  'react-markdown',
  'marked',
  'dompurify',
  'sanitize-html',
  'parse5',
  'htmlparser2',
].map((name) => ({ name, message: 'Prohibido: el frontend no interpreta HTML/Markdown (FE-009).' }));

const MOCKS_PATTERN = {
  group: ['**/mocks', '**/mocks/**'],
  message: 'El cálculo del mock-servidor vive solo en src/mocks/** (FE-003).',
};
const TRANSPORT_PATTERN = {
  group: ['**/api/transport', '**/api/transport.ts'],
  message: 'Las vistas usan data/queries.ts y data/mutations.ts, nunca el transporte (§4.1).',
};

const restrictedImports = (...patterns) => [
  'error',
  { paths: FORBIDDEN_HTML_PACKAGES, ...(patterns.length > 0 ? { patterns } : {}) },
];

const restrictedSyntax = [
  'error',
  { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: 'Prohibido dangerouslySetInnerHTML (FE-009).' },
  {
    selector: 'MemberExpression[property.name=/^(innerHTML|outerHTML|insertAdjacentHTML|srcdoc|createContextualFragment)$/]',
    message: 'Prohibido inyectar HTML (FE-009).',
  },
  { selector: "JSXAttribute[name.name='srcDoc']", message: 'Prohibido srcdoc (FE-009).' },
  { selector: "CallExpression[callee.name='eval']", message: 'Prohibido eval.' },
  { selector: "NewExpression[callee.name='Function']", message: 'Prohibido new Function.' },
  { selector: "CallExpression[callee.name='Function']", message: 'Prohibido Function().' },
  { selector: "NewExpression[callee.name='DOMParser']", message: 'Prohibido DOMParser (FE-009).' },
];

const restrictedProperties = [
  'error',
  { object: 'document', property: 'write', message: 'Prohibido document.write.' },
  { object: 'document', property: 'writeln', message: 'Prohibido document.writeln.' },
  { object: 'window', property: 'eval', message: 'Prohibido eval.' },
  { object: 'globalThis', property: 'eval', message: 'Prohibido eval.' },
];

const restrictedGlobals = [
  'error',
  { name: 'eval', message: 'Prohibido eval.' },
  { name: 'DOMParser', message: 'Prohibido DOMParser (FE-009).' },
];

export default tseslint.config(
  // NIT 5: el primer elemento ignora salidas de build/pruebas y los generados
  // (los generados siguen cubiertos por src/security.static.test.ts).
  { ignores: ['dist/**', 'test-results/**', 'playwright-report/**', 'blob-report/**', 'src/api/generated/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx,js}'],
    ...jsxA11y.flatConfigs.recommended,
    languageOptions: {
      ...jsxA11y.flatConfigs.recommended.languageOptions,
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.browser },
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    ...reactHooks.configs.flat.recommended,
  },
  {
    files: ['**/*.{ts,tsx,js,mjs}'],
    rules: {
      'no-console': 'error',
      'no-restricted-syntax': restrictedSyntax,
      'no-restricted-properties': restrictedProperties,
      'no-restricted-globals': restrictedGlobals,
      'no-restricted-imports': restrictedImports(),
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    },
  },
  {
    // FE-003: features/data/domain no importan el mock-servidor.
    files: ['src/data/**/*.{ts,tsx}', 'src/domain/**/*.{ts,tsx}'],
    rules: { 'no-restricted-imports': restrictedImports(MOCKS_PATTERN) },
  },
  {
    // §4.1: las vistas tampoco importan el transporte.
    files: ['src/features/**/*.{ts,tsx}'],
    rules: { 'no-restricted-imports': restrictedImports(MOCKS_PATTERN, TRANSPORT_PATTERN) },
  },
  {
    // Única vía de logs (§6.4).
    files: ['src/lib/log.ts'],
    rules: { 'no-console': 'off' },
  },
  {
    // Scripts de Node y configuración: salida por consola permitida, globals de Node.
    files: ['scripts/**/*.mjs', 'vite.config.ts', 'vite-plugins/**/*.ts', 'playwright.config.ts', 'e2e/**/*.ts', 'eslint.config.js'],
    languageOptions: { globals: { ...globals.node } },
    rules: { 'no-console': 'off' },
  },
);
