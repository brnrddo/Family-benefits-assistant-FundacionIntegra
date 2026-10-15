# Frontend

## Objetivo

Construir la PWA mobile-first para la educadora: lista del jardín con acciones prioritarias por familia, ficha familiar, preguntas, recomendaciones, conversación y KPI, utilizable con poca conexión.

- **Dueño:** Ingeniería Eléctrica.
- **Colaboradores:** Computación entrega contratos/API; Recursos Naturales valida lenguaje, privacidad y pruebas manuales.

## Entradas y salidas

**Entradas:** API o mocks con familias, RSH, evaluaciones, acceso, prioridad, preguntas, recomendaciones y KPI.

**Salidas:** vistas accesibles, aviso referencial, registro de conversación y presentación separada de beneficios personalizados y generales.

## Dependencias y límites

Depende del contrato C3 (`.kiro/specs/_shared/contracts/C3-api.openapi.yaml`) y del copy/C4 de Rol 4 (`content/`). Trabaja con mocks C3 sintéticos hasta tener el API real.

No colocar aquí reglas de elegibilidad, cálculos alternativos de prioridad, secretos, acceso directo a datos canónicos ni datos personales en almacenamiento o logs. El navegador muestra lo que entrega C3: no recalcula elegibilidad, acceso, ranking U/B/V ni porcentajes (FE-003).

## Cómo correr (desde `frontend/`, Node 22.22+ o 24.15+)

```powershell
npm ci
npm run dev:mock     # perfil local + mocks C3 sintéticos en proceso (sin backend); abre http://localhost:5173
npm run check        # typecheck → lint → vitest → build → presupuesto de bundle
npx playwright install chromium   # solo la primera vez, para los e2e
npm run test:e2e     # smoke Playwright a 360 px (construye `build:e2e` y lo sirve en :4173)
```

Para ver la app como celular, use el modo dispositivo del navegador a 360 px. Sin `content/i18n/es.json` (rama `contenido`) la consola de Vite avisa `copy MOCK_LOCAL` y `C4 MISSING`: es lo esperado en la rama `front`.

Vistas: Mi jardín (`/`, familias en orden neutro con sus acciones prioritarias, DEC-037), Ficha (`/familias/:id`, con nombre de trato local DEC-038 y beneficios en dos grupos), Guion, Mensaje e impresión, Marcar conversado (`/familias/:id/conversacion`, 3 toques), Agregar información (`/familias/:id/agregar-informacion`, operación propuesta fuera de C3, solo con mocks salvo `VITE_PROPOSAL_ADD_INFO=true`; ver `docs/PROPUESTA_C3_agregar_informacion.md`, DEC-039), Familia nueva (`/familia-nueva`, no existe en `escala`), Avance (`/avance`) y Preguntar (`/preguntar`). Los mocks aceptan escenarios con `?mock=` al cargar (p. ej. `conv503`, `kpiSuppressed`, `assistantDeterministic`; lista en `src/mocks/scenarios.ts`).

| Script | Para qué |
|---|---|
| `dev`, `dev:mock`, `dev:api` | Vite dev con variables del entorno, con mocks, o contra la API local de Rol 2 |
| `build`, `build:e2e`, `build:demo-rehearsal` | Build estático `dist/` (real, e2e con mocks, ensayo Demo con mocks y copy provisional) |
| `preview` | Sirve `dist/` en `http://localhost:4173` |
| `typecheck`, `lint`, `test`, `test:e2e` | TypeScript, ESLint (`--max-warnings=0`), Vitest, Playwright |
| `gen:contract` | Regenera tipos y validadores Ajv desde C3 (`src/api/generated/`) |
| `gen:proposals` | Regenera el validador del schema local de la operación propuesta (`src/api/proposals/generated/`) |
| `check:api` | Valida los GET de una API loopback contra C3 (sin bodies ni POST) |

Copy: sin `content/i18n/es.json` canónico se usa el copy provisional `src/i18n/es.mock.ts` con la insignia "Textos provisionales" (SUP-030); solo se permite en `local` o en `demo` con `BRUJULA_ALLOW_MOCK_COPY=true`. Polly/Translate quedan ocultos mientras C4 no los active con evidencia y C3 no tenga ruta (PREG-031).

## Conectar con la API real (Rol 2)

Las vistas solo conocen el cliente C3 (`src/api/client.ts`); pasar de mocks a la API real es solo una variable.

- **Con mocks:** `npm run dev:mock` (MSW en proceso, datos sintéticos).
- **Con la API local de Rol 2:** levante el backend en loopback sirviendo C3 bajo `/api/v1` y ejecute, desde `frontend/`:

  ```powershell
  $env:BRUJULA_DEV_API_PROXY = 'http://127.0.0.1:8000'   # puerto del backend; por defecto 8000
  npm run dev:api
  ```

  El modo `api` usa el perfil `local` (capacidades Demo: caché y cola sintéticas), sin Cognito, y el proxy de Vite `/api/v1 → BRUJULA_DEV_API_PROXY` (sin CORS). Solo acepta URLs loopback; con otra URL el proxy queda desactivado y se avisa en consola.
- **Verificar el contrato antes de la demo:** `npm run check:api` (o `npm run check:api -- http://127.0.0.1:8000/api/v1`, o `BRUJULA_API_CHECK_URL`). Recorre los GET de C3 (jardines, familias, ficha, contexto, oportunidades en los 3 órdenes, KPI nacional y por jardín) encadenando el primer jardín y la primera familia, valida cada respuesta con los validadores Ajv generados e imprime `OK`/`FAIL` por ruta normalizada. No hace POST, no envía tokens y nunca vuelca bodies: ante `FAIL` solo muestra status, media type o `instancePath` + `keyword` del schema. Sale con 1 si alguna ruta falla y con 2 si la URL no es loopback.

## Despliegue de referencia en AWS (NO_VERIFICADO)

> **Estado: NO_VERIFICADO.** Nada de esto se ha desplegado ni probado en una cuenta AWS. Los recursos (app Amplify, bucket, distribución, Cognito, API) los crea Rol 2 con IaC (PREG-032, PREG-033); este frontend solo entrega el build estático y la configuración esperada (DEC-035).

La PWA es un **sitio estático**: `npm ci && npm run build` genera `frontend/dist/` (`index.html`, `assets/*` con hash, `sw.js`, `workbox-*.js`, `manifest.webmanifest`, `icons/`). No hay servidor de aplicación ni SDK de AWS en el navegador; la UI solo llama a C3 por HTTPS.

### Variables por perfil (se fijan al compilar)

Las `VITE_*` quedan embebidas en el JS del build, así que **nunca** llevan secretos (client ID, pool y dominio Cognito son públicos en OIDC con cliente público + PKCE). Nombres y validación en `.env.example`; la app falla cerrada con una pantalla de configuración si no calzan.

| Caso | `VITE_PROFILE` | `VITE_USE_MOCKS` | `VITE_API_BASE_URL` | `VITE_AUTH_MODE` | `VITE_DATA_CLASSIFICATION` |
|---|---|---|---|---|---|
| Ensayo Demo estático (sin API) | `demo` | `true` | — | `none` | `SYNTHETIC_DEMO_NOT_A_REAL_PERSON` |
| Demo con API cloud | `demo` | `false` | `https://<api>/api/v1` | `cognito` + `VITE_COGNITO_*` | `SYNTHETIC_DEMO_NOT_A_REAL_PERSON` |
| Escala (piloto Integra) | `escala` | `false` | `https://<api>/api/v1` | `cognito` + `VITE_COGNITO_*` | — (sin caché ni cola) |

Cognito solo entra cuando la PWA habla con una API cloud: el ensayo estático con mocks y el fallback loopback no lo usan, y una API fuera de loopback **sin** Cognito no arranca (DEC-032). El ensayo estático se construye con `npm run build:demo-rehearsal` (ya fija las variables de la primera fila). Un build `demo` o `escala` real exige el copy canónico de Rol 4 en `../content` (o `BRUJULA_CONTENT_DIR`); con copy provisional el build falla a propósito.

### Opción A — Amplify Hosting (Demo)

App conectada al repositorio (monorepo, `appRoot: frontend`) con este `amplify.yml` de referencia:

```yaml
version: 1
applications:
  - appRoot: frontend
    frontend:
      phases:
        preBuild:
          commands: [npm ci]
        build:
          commands: [npm run build]   # o npm run build:demo-rehearsal para el ensayo con mocks
      artifacts:
        baseDirectory: dist
        files: ['**/*']
      cache:
        paths: [node_modules/**/*]
```

- Variables `VITE_*` (y `BRUJULA_CONTENT_DIR` si el copy no está en `../content`) en *Environment variables* de la app, nunca en el repo.
- Reescritura SPA: origen `</^[^.]+$|\.(?!(css|js|json|map|png|svg|ico|txt|webmanifest|woff2?)$)([^.]+$)/>`, destino `/index.html`, tipo `200`.
- Headers (*Custom headers*): `Cache-Control: no-cache` para `/index.html`, `/sw.js` y `/manifest.webmanifest`; `Cache-Control: public, max-age=31536000, immutable` para `/assets/*`; en `/**`: `Content-Security-Policy: frame-ancestors 'none'` (el resto de la CSP ya va como `<meta>` en `index.html`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- Cognito: agregar la URL de Amplify como *allowed callback* (`/auth/callback`) y *sign-out URL* (`/`) del app client.

### Opción B — S3 + CloudFront OAC (Escala)

- Bucket S3 **privado** (Block Public Access activo), distribución CloudFront con OAC, `index.html` como objeto raíz y HTTPS obligatorio. CloudFront sirve solo assets: la API va directo a API Gateway (sin proxy por CloudFront).
- SPA: respuestas personalizadas 403/404 → `/index.html` con 200.
- *Response headers policy* con los mismos headers de seguridad de la opción A.
- Publicación (con credenciales del pipeline de Rol 2, no desde el navegador):

  ```powershell
  aws s3 sync dist/ s3://<bucket>/ --delete --exclude index.html --exclude sw.js --exclude manifest.webmanifest --cache-control "public,max-age=31536000,immutable"
  aws s3 cp dist/index.html s3://<bucket>/index.html --cache-control "no-cache"
  aws s3 cp dist/sw.js s3://<bucket>/sw.js --cache-control "no-cache"
  aws s3 cp dist/manifest.webmanifest s3://<bucket>/manifest.webmanifest --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id <id> --paths /index.html /sw.js /manifest.webmanifest
  ```

### Qué falta verificar en AWS

App Amplify o bucket/distribución reales, reescritura SPA y headers en respuesta, Cognito (callback/logout, scopes, PKCE), CORS de la API para el origen de la PWA (incluidas respuestas de error) e instalación de la PWA en un celular. Todo queda `NO_VERIFICADO` hasta un smoke test fechado (DEC-017).

Contexto: [especificación](../docs/especificacion/PROYECTO_3_ESPECIFICACION_v2.md), [roles](../docs/equipo/ROLES_Y_RESPONSABILIDADES.md), [estructura](../docs/arquitectura/ESTRUCTURA_REPOSITORIO.md) y [flujo de ficha](../docs/producto/FLUJO_DE_FICHA.md).
