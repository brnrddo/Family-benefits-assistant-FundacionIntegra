import { describe, expect, it } from 'vitest';
import { toSafeHttpsUrl } from './safeUrl';

describe('domain/safeUrl', () => {
  it('acepta https y normaliza', () => {
    expect(toSafeHttpsUrl('https://www.example.cl/beneficio')).toBe('https://www.example.cl/beneficio');
    expect(toSafeHttpsUrl('HTTPS://WWW.EXAMPLE.CL')).toBe('https://www.example.cl/');
  });

  it('rechaza http, javascript, data, credenciales y basura', () => {
    for (const bad of [
      'http://www.example.cl',
      'javascript:alert(1)',
      ' javascript:alert(1)',
      'JAVASCRIPT:alert(1)',
      'data:text/html,<b>x</b>',
      'https://user:pass@www.example.cl',
      'https://user@www.example.cl',
      '//www.example.cl',
      '/ruta/relativa',
      'no es url',
      '',
      42,
      null,
      `https://www.example.cl/${'a'.repeat(2050)}`,
    ]) {
      expect(toSafeHttpsUrl(bad)).toBeNull();
    }
  });
});
