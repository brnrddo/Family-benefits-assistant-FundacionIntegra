// Corte automático del nombre de trato a "PrimerNombre I." (DEC-047). Nombres inventados
// (SYNTHETIC_DEMO_NOT_A_REAL_PERSON); no corresponden a personas reales.
import { describe, expect, it } from 'vitest';
import { cutLocalName } from './localNames';

describe('cutLocalName (DEC-047)', () => {
  it.each([
    ['Sofía Martínez', 'Sofía M.'],
    ['  sofía   martínez  ', 'Sofía M.'],
    ['SOFÍA', 'Sofía'],
    ['ana-maría pérez soto', 'Ana-María P.'],
    ["d'angelo rojas", "D'Angelo R."],
    // Limitación documentada: los nombres compuestos se cortan.
    ['María José Pérez', 'María J.'],
    ['ñuño ñandú', 'Ñuño Ñ.'],
    // Idempotente: un nombre ya cortado no cambia.
    ['Sofía M.', 'Sofía M.'],
  ])('%j → %j', (raw, expected) => {
    expect(cutLocalName(raw)).toEqual({ ok: true, value: expected });
  });

  it.each([
    ['', 'empty'],
    ['Sofía 2', 'invalid_chars'],
    ['sofia@correo', 'invalid_chars'],
  ])('%j → error %s', (raw, issue) => {
    expect(cutLocalName(raw)).toEqual({ ok: false, issue });
  });
});
