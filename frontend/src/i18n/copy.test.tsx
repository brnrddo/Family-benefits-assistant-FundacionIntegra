import { render, screen } from '@testing-library/react';
import { copySource, copyValues } from 'virtual:brujula-content';
import { describe, expect, it } from 'vitest';
import meta from '../api/generated/c3.meta.json';
import { validateFamiliaDetailEnvelope } from '../api/generated/validators.gen.js';
import { fichaBrecha } from '../test/fixtures';
import { COPY_KEYS } from './catalog';
import { benefitName, t, yearsLabel } from './copy';

describe('i18n — t() y benefitName (§7.3)', () => {
  it('en pruebas (perfil local sin es.json) el copy resuelto es MOCK_LOCAL completo', () => {
    expect(copySource).toBe('MOCK_LOCAL');
    for (const key of COPY_KEYS) expect(typeof copyValues[key]).toBe('string');
  });

  it('interpola placeholders como texto, sin interpretar markup', () => {
    expect(t('home.progress', { informed: 3, total: 8 })).toBe('3 de 8 familias conversadas');
    expect(t('family.title', { family_id: '<b>FAM</b>' })).toBe('Familia <b>FAM</b>');
    render(<p>{t('family.title', { family_id: '<img src=x onerror=alert(1)>' })}</p>);
    expect(screen.getByText('Familia <img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(document.querySelector('img')).toBeNull();
  });

  it('edad con singular y plural (NIT-05)', () => {
    expect(yearsLabel(1, '1')).toBe('1 año');
    expect(yearsLabel(0, '0')).toBe('0 años');
    expect(yearsLabel(4, '4')).toBe('4 años');
  });

  it('no reemplaza placeholders no declarados', () => {
    expect(t('common.years', { age: 4 })).toBe('4 años');
    expect(t('app.name')).toBe('Brújula Familiar');
  });

  it('benefitName: simple_title de C3 > clave opcional > ID', () => {
    expect(benefitName('BEN-001', 'Aporte mensual por hijo')).toBe('Aporte mensual por hijo');
    expect(benefitName('BEN-001')).toBe('Beneficio BEN-001 (nombre provisional)');
    expect(benefitName('BEN-999')).toBe('BEN-999');
  });

  it('el aviso de t() valida como disclaimer const de C3 en un envelope', () => {
    const envelope = fichaBrecha();
    envelope.data.disclaimer = t('notice.referential') as typeof envelope.data.disclaimer;
    expect(validateFamiliaDetailEnvelope(envelope)).toBe(true);
    expect(t('notice.referential')).toBe(meta.disclaimer);
  });
});
