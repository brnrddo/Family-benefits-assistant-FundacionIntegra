// Prueba estática de seguridad (design.md §11.2, FE-009): recorre src/**/*.{ts,tsx,js}, INCLUIDOS
// los generados (que ESLint ignora por el NIT 5), y falla ante APIs de inyección de HTML,
// evaluación dinámica o parsers HTML/Markdown. Los patrones se arman por partes para que este
// archivo no se detecte a sí mismo.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SELF_URL = import.meta.url;
const SRC_DIR = path.dirname(fileURLToPath(SELF_URL));
const SELF = fileURLToPath(SELF_URL);

const j = (...parts: string[]) => parts.join('');
const FORBIDDEN: readonly [string, RegExp][] = [
  ['dangerouslySetInnerHTML', new RegExp(`\\b${j('dangerously', 'SetInner', 'HTML')}\\b`)],
  ['innerHTML', new RegExp(`\\b${j('inner', 'HTML')}\\b`)],
  ['outerHTML', new RegExp(`\\b${j('outer', 'HTML')}\\b`)],
  ['insertAdjacentHTML', new RegExp(`\\b${j('insertAdjacent', 'HTML')}\\b`)],
  ['srcdoc', new RegExp(`\\b${j('src', 'doc')}\\b`, 'i')],
  ['createContextualFragment', new RegExp(`\\b${j('createContextual', 'Fragment')}\\b`)],
  ['document.write', new RegExp(`\\bdocument\\s*\\.\\s*${j('wri', 'te')}(ln)?\\b`)],
  ['DOMParser', new RegExp(`\\b${j('DOM', 'Parser')}\\b`)],
  ['eval(', new RegExp(`\\b${j('ev', 'al')}\\s*\\(`)],
  ['new Function', new RegExp(`\\bnew\\s+${j('Func', 'tion')}\\b`)],
  ['Function(', new RegExp(`(^|[^.\\w])${j('Func', 'tion')}\\s*\\(`)],
  [
    'parser HTML/Markdown',
    new RegExp(`(from\\s+|import\\s*\\(\\s*|require\\s*\\(\\s*)['"](${['html-react-parser', 'react-markdown', 'marked', 'dompurify', 'sanitize-html', 'parse5', 'htmlparser2'].join('|')})['"/]`),
  ],
];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(ts|tsx|js)$/.test(name) && full !== SELF) out.push(full);
  }
  return out;
}

describe('prueba estática de seguridad (§11.2)', () => {
  const files = walk(SRC_DIR);

  it('recorre el código fuente incluidos los validadores generados', () => {
    const relative = files.map((f) => path.relative(SRC_DIR, f).split(path.sep).join('/'));
    expect(relative).toContain('api/generated/validators.gen.js');
    expect(relative).toContain('api/contract/runtime.js');
    expect(relative).toContain('main.tsx');
  });

  it.each(FORBIDDEN)('sin %s', (_label, pattern) => {
    const offenders = files.filter((file) => pattern.test(readFileSync(file, 'utf8')));
    expect(offenders.map((f) => path.relative(SRC_DIR, f))).toEqual([]);
  });

  it('los patrones detectan los tokens prohibidos (control positivo)', () => {
    const samples = [
      `<div ${j('dangerously', 'SetInner', 'HTML')}={x} />`,
      `el.${j('inner', 'HTML')} = x`,
      `${j('ev', 'al')}("1")`,
      `new ${j('Func', 'tion')}("return 1")`,
      `import x from '${j('dom', 'purify')}'`,
    ];
    samples.forEach((sample) => expect(FORBIDDEN.some(([, re]) => re.test(sample)), sample).toBe(true));
  });
});
