// Valores inventados con formato de RUT/teléfono/correo: no corresponden a personas reales.
import { describe, expect, it } from 'vitest';
import { containsPii, detectPii } from './piiGuard';

describe('domain/piiGuard', () => {
  it('detecta RUT con y sin puntos/guion', () => {
    for (const text of ['mi rut es 11.111.111-1', '11111111-1', '9.999.999-K', '12345678k']) {
      expect(detectPii(text)).toContain('rut');
    }
  });

  it('detecta teléfonos chilenos', () => {
    for (const text of ['llamar al +56 9 1234 5678', '912345678', '56 9 8765 4321']) {
      expect(detectPii(text)).toContain('phone');
    }
  });

  it('detecta correos', () => {
    expect(detectPii('escribir a persona@correo.example')).toContain('email');
  });

  it('no bloquea preguntas generales', () => {
    for (const text of ['¿Qué apoyos existen para niños en jardín?', '¿Dónde se actualiza el Registro Social de Hogares?']) {
      expect(containsPii(text)).toBe(false);
    }
  });

  it('falla cerrado ante un falso positivo (9 dígitos)', () => {
    expect(containsPii('código 912345678 del formulario')).toBe(true);
  });
});
