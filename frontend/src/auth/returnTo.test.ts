import { describe, expect, it } from 'vitest';
import { sanitizeReturnTo } from './returnTo';

describe('auth/returnTo (§14.1)', () => {
  it('conserva rutas conocidas y su query validada', () => {
    expect(sanitizeReturnTo('/')).toBe('/');
    expect(sanitizeReturnTo('/?jardin=JAR-SIM-E3-00001')).toBe('/?jardin=JAR-SIM-E3-00001');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001')).toBe('/familias/FAM-SIM-E3-00001');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001?orden=urgencia')).toBe('/familias/FAM-SIM-E3-00001?orden=urgencia');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001/conversacion')).toBe('/familias/FAM-SIM-E3-00001/conversacion');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001/guion')).toBe('/familias/FAM-SIM-E3-00001/guion');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001/mensaje')).toBe('/familias/FAM-SIM-E3-00001/mensaje');
    expect(sanitizeReturnTo('/familia-nueva?jardin=JAR-SIM-E3-00002')).toBe('/familia-nueva?jardin=JAR-SIM-E3-00002');
    expect(sanitizeReturnTo('/avance')).toBe('/avance');
    expect(sanitizeReturnTo('/asistente')).toBe('/asistente');
  });

  it('descarta query desconocida o inválida y el hash', () => {
    expect(sanitizeReturnTo('/?jardin=../x&otro=1#frag')).toBe('/');
    expect(sanitizeReturnTo('/familias/FAM-SIM-E3-00001?orden=hack&pregunta=hola')).toBe('/familias/FAM-SIM-E3-00001');
  });

  it.each([
    '//evil.example',
    'https://evil.example',
    '/\\evil',
    '/\\/evil.example',
    'javascript:alert(1)',
    'evil',
    '',
    '/familias/../../etc',
    '/familias/fam-minuscula',
    '/desconocida',
    '/auth/callback',
    `/${'a'.repeat(600)}`,
    '/ familias',
    '/\tfamilias',
  ])('returnTo hostil %j → /', (hostile) => {
    expect(sanitizeReturnTo(hostile)).toBe('/');
  });

  it('valores no string → /', () => {
    expect(sanitizeReturnTo(undefined)).toBe('/');
    expect(sanitizeReturnTo(null)).toBe('/');
    expect(sanitizeReturnTo({ returnTo: '/' })).toBe('/');
  });
});
