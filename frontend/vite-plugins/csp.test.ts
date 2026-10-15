import { describe, expect, it } from 'vitest';
import { buildCsp, isLoopbackHttpUrl, safeOrigin } from './csp';

describe('CSP (§15)', () => {
  it('sin API ni Cognito: solo self, sin inline ni eval', () => {
    const csp = buildCsp({});
    expect(csp).toBe(
      "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'",
    );
    expect(csp).not.toMatch(/unsafe-inline|unsafe-eval|frame-ancestors/);
  });

  it('agrega solo ORÍGENES https (o http loopback) de API y Cognito', () => {
    const csp = buildCsp({
      apiBaseUrl: 'https://api.brujula-demo.example/api/v1',
      cognitoAuthority: 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_SIMPOOL01',
      cognitoDomain: 'https://auth.brujula-demo.example',
    });
    expect(csp).toContain(
      "connect-src 'self' https://api.brujula-demo.example https://cognito-idp.us-east-1.amazonaws.com https://auth.brujula-demo.example",
    );
    expect(csp).toContain("form-action 'self' https://auth.brujula-demo.example");
    expect(csp).not.toContain('/api/v1');
  });

  it('descarta valores inseguros', () => {
    expect(safeOrigin('http://api.brujula-demo.example')).toBeNull();
    expect(safeOrigin('https://u:p@api.brujula-demo.example')).toBeNull();
    expect(safeOrigin('javascript:alert(1)')).toBeNull();
    expect(safeOrigin('/api/v1')).toBeNull();
    expect(safeOrigin('http://localhost:8000/api/v1')).toBe('http://localhost:8000');
    expect(isLoopbackHttpUrl('http://127.0.0.1:8000')).toBe(true);
    expect(isLoopbackHttpUrl('http://api.brujula-demo.example')).toBe(false);
  });
});
