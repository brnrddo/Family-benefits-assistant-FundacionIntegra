# Evidencia AWS fechada — Demo E-3 (2026-10-15, us-east-1)

Bitácora sanitizada de los smoke tests que mueven los ocho servicios del núcleo de
`NO_VERIFICADO` a `VERIFICADO_EN_CUENTA` en [`ARQUITECTURA_AWS.md`](../ARQUITECTURA_AWS.md).
Cumple el registro documental de evidencia de **API-T09** y la regla de
[`PRIVACIDAD_DEMO.md`](../PRIVACIDAD_DEMO.md): fecha, región efectiva, operación y
resultado sanitizado. Lo que no está probado aquí sigue sin estarlo.

**Formato obligatorio de cada línea:** `fecha | región | operación | OK/FALLA | detalle sanitizado`.

**Qué no aparece y no va a aparecer:** número de cuenta, ARN completos, nombre del
bucket, `guardrailId`, id o URL de la HTTP API, dominio de Amplify, ids de grupo de
usuarios o de cliente de Cognito, dominio de inicio de sesión, tokens, contraseñas y
enlaces del panel del evento. Se usan marcadores genéricos (`<bucket>`, `<guardrailId>`,
`<apiId>`, `<poolId>`, `<clientId>`, `<dominioAmplify>`). Los valores reales viven fuera
del repositorio y entran al runtime solo por variables `E3_*` y `VITE_*` (DEC-048,
DEC-090). La región `us-east-1` y el id del modelo sí son públicos: los fija el evento.

**Entorno e identidad.** Todo se ejecutó desde **AWS CloudShell**, no desde el escritorio
Kiro del evento. Identidad efectiva `assumed-role/WSParticipantRole/Participant`, o sea la
de la sesión de consola, sin credenciales en ningún disco local. CloudShell corre Amazon
Linux 2023 con Python 3.13, `git` y `zip` preinstalados y ~906 MB libres en `$HOME`.

**Datos.** Solo el dataset sintético E-3 (`SYNTHETIC_DEMO_NOT_A_REAL_PERSON`): 500
familias, 20 beneficios, 10.000 evaluaciones y 10.000 accesos. Nada real tocó la cuenta.

## Qué quedó verificado

| Servicio del núcleo | Estado 2026-10-15 | Bloque de evidencia |
|---|---|---|
| Bedrock Converse | VERIFICADO_EN_CUENTA | A |
| Bedrock Guardrails | VERIFICADO_EN_CUENTA | B |
| Lambda (zip + Mangum) | VERIFICADO_EN_CUENTA | D |
| API Gateway HTTP API | VERIFICADO_EN_CUENTA | D y D-bis |
| S3 privado | VERIFICADO_EN_CUENTA | E |
| DynamoDB (tabla y TTL) | VERIFICADO_EN_CUENTA | E |
| Cognito + autorizador JWT | VERIFICADO_EN_CUENTA | F |
| Amplify Hosting | VERIFICADO_EN_CUENTA | G |

CloudWatch recibe los logs de la Lambda, pero la retención corta no se fijó: sigue
`NO_VERIFICADO` (bloque H, no ejecutado).

## Bloque A — Bedrock

```
2026-10-15 | us-east-1 | sts:GetCallerIdentity | OK | identidad = assumed-role WSParticipantRole/Participant (rol prestado, sin llaves)
2026-10-15 | us-east-1 | bedrock:ListInferenceProfiles | OK | 34 perfiles SYSTEM_DEFINED de Anthropic visibles; incluye us.anthropic.claude-haiku-4-5-20251001-v1:0
2026-10-15 | us-east-1 | bedrock-runtime:Converse | OK | modelo us.anthropic.claude-haiku-4-5-20251001-v1:0 respondio "OK" con maxTokens=10, temperature=0
```

El formulario de caso de uso de Anthropic ya estaba aprobado en la cuenta del evento:
`converse` no devolvió `AccessDeniedException`. Riesgo cerrado.

Modelo confirmado: `us.anthropic.claude-haiku-4-5-20251001-v1:0` (perfil de inferencia
versionado). Respaldos disponibles en la cuenta si Haiku redacta mal:
`us.anthropic.claude-sonnet-4-5-20250929-v1:0` y `us.anthropic.claude-sonnet-4-6`. Se
mantienen descartados Fable 5 y los GPT-5.x, que exigen cambiar la retención de datos.

## Bloque B — Guardrails

```
2026-10-15 | us-east-1 | bedrock:CreateGuardrail | OK | PROMPT_ATTACK HIGH solo en entrada; HATE/INSULTS/MISCONDUCT/VIOLENCE/SEXUAL HIGH en entrada y salida; EMAIL/PHONE/ADDRESS en ANONYMIZE; regex de RUT en BLOCK
2026-10-15 | us-east-1 | bedrock:CreateGuardrailVersion | OK | version publicada = 1
2026-10-15 | us-east-1 | bedrock-runtime:ApplyGuardrail | OK | source=INPUT con intento de manipulacion del prompt -> GUARDRAIL_INTERVENED (bloqueo correcto)
2026-10-15 | us-east-1 | bedrock-runtime:ApplyGuardrail | OK | source=INPUT con pregunta legitima sobre un beneficio -> NONE (sin falso positivo)
```

El `guardrailId` y la versión no son secretos, pero no se publican acá: entran al runtime
por `E3_GUARDRAIL_ID` y `E3_GUARDRAIL_VERSION`.

Recordatorio de la política: Guardrails es la **segunda** barrera. La primera y decisiva
sigue siendo el filtro por allowlist (`LlmContextV1`) del backend, que falla cerrado.
Guardrails no anonimiza nada por sí solo.

No se incluyó el filtro de PII `NAME` a propósito: los mensajes a la familia pueden llevar
nombres de trato sintéticos (DEC-038, DEC-047) y el filtro los taparía.

## Bloque D — Lambda (zip + Mangum)

```
2026-10-15 | us-east-1 | pip install --platform manylinux2014_x86_64 --python-version 3.12 | OK | wheels Linux resueltos para todo el arbol; los conflictos que reporta pip son del aws-sam-cli preinstalado en CloudShell, no del paquete (instalacion con --target aislada)
2026-10-15 | us-east-1 | build_lambda.sh | OK | brujula-api.zip = 18,1 MB comprimido / 45 MB descomprimido; bajo el limite de 50 MB de subida directa y muy bajo el de 250 MB descomprimido
2026-10-15 | us-east-1 | verificacion de contenido del zip | OK | sin *.db ni *.sqlite, sin backend/tests, sin .env; presentes lambda_function.py en la raiz, C3-api.openapi.yaml y content/manifest.yaml. Unico .pem = botocore/cacert.pem (130 certificados publicos, 0 llaves privadas): es el bundle de CA, no un secreto
2026-10-15 | us-east-1 | iam:CreateRole | OK | rol de ejecucion creado con trust policy de lambda.amazonaws.com
2026-10-15 | us-east-1 | iam:AttachRolePolicy | OK | AWSLambdaBasicExecutionRole adjuntado (logs a CloudWatch)
2026-10-15 | us-east-1 | iam:PutRolePolicy | OK | politica inline de minimo privilegio: un perfil de inferencia, un guardrail, solo snapshots/* del bucket y GetItem/PutItem/Query sobre una tabla
2026-10-15 | us-east-1 | lambda:CreateFunction | OK | runtime python3.12, handler lambda_function.handler, memoria 1024 MB, timeout 29 s; Pending -> Active
2026-10-15 | us-east-1 | lambda:Invoke | OK | evento HTTP API v2 sintetico sobre GET /healthz -> StatusCode 200, FunctionError null, cuerpo {"status":"ok"} y cabecera x-request-id presente
```

Queda probado el camino zip → Mangum → FastAPI dentro de la nube. CloudShell también puede
crear roles de IAM, otra duda que la guía dejaba abierta.

## Bloque D-bis — HTTP API, snapshot y motor real

```
2026-10-15 | us-east-1 | apigatewayv2:CreateApi | OK | HTTP API con ruta $default, etapa $default con AutoDeploy e integracion AWS_PROXY formato 2.0
2026-10-15 | us-east-1 | lambda:AddPermission | OK | apigateway.amazonaws.com autorizado a invocar la funcion, acotado al id de la API
2026-10-15 | us-east-1 | GET /healthz via HTTP API | OK | 404 en el primer intento por carrera del despliegue automatico; al reintentar, 200 con {"status":"ok"}
2026-10-15 | us-east-1 | loader + build_views (CloudShell) | OK | 23 tablas, 28.585 filas, 500 familias, 20 beneficios, 10.000 evaluaciones y 10.000 accesos en 5,66 s (objetivo < 30 s); e3.db = 21 MB
2026-10-15 | us-east-1 | s3:PutObject snapshots/e3.db | OK | 20,6 MiB subidos al bucket privado; solo datos sinteticos
2026-10-15 | us-east-1 | lambda:UpdateFunctionConfiguration | OK | variables E3_* completas (Bedrock incluido, con E3_LLM_PROVIDER=stub); el cambio fuerza arranque en frio y descarta las copias con /tmp viejo
2026-10-15 | us-east-1 | arranque en frio con snapshot | OK | log: e3_db_descargada bytes=21618688
2026-10-15 | us-east-1 | motor real en la nube | OK | log: motor_real_snapshot_listo familias=500 jardines=50 build_s=2.52; SIN runtime_degradado_a_mock
2026-10-15 | us-east-1 | GET /api/v1/jardines via HTTP API | OK | 200, latencia 2996 ms en frio (Init 2471 ms, billed 5573 ms, memoria 192 MB de 1024); la ruta pagina de 25 en 25 sobre los 50 jardines reales
```

**La trampa de la degradación silenciosa queda descartada con evidencia.** El log del
arranque en frío confirma el motor real sobre la SQLite sintética bajada de S3 a `/tmp`, no
mocks. Es el hito funcional del día.

**Nota de rendimiento para el ensayo:** el arranque en frío cuesta unos 5,5 s en total. Hay
que despertar la función con una petición antes de presentar.

## Bloque E — S3 privado y DynamoDB

```
2026-10-15 | us-east-1 | s3:CreateBucket | OK | bucket privado creado para snapshots sinteticos (nombre fuera del repo)
2026-10-15 | us-east-1 | s3:PutPublicAccessBlock | OK | BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy y RestrictPublicBuckets en true
2026-10-15 | us-east-1 | s3:GetPublicAccessBlock | OK | las cuatro banderas confirmadas en true (exigencia del evento)
2026-10-15 | us-east-1 | dynamodb:CreateTable | OK | tabla unica, PAY_PER_REQUEST, pk HASH + sk RANGE -> CREATING -> ACTIVE (wait table-exists sin error)
2026-10-15 | us-east-1 | dynamodb:UpdateTimeToLive | OK | TTL habilitado sobre el atributo ttl
2026-10-15 | us-east-1 | dynamodb:DescribeTimeToLive | OK | TimeToLiveStatus = ENABLED, AttributeName = ttl (confirmado)
```

Uso previsto de la tabla, según la política de privacidad:

- Caché de textos: `pk = CACHE#<hash del envelope filtrado + versiones>`, `sk = v1`, con `ttl`. **Sin id de familia.**
- Conversaciones: `pk = CONV#<id sintetico>`, `sk = <fecha ISO>`.

**La tabla está creada y verificada, pero el runtime todavía no la usa.** La caché de textos
y el registro de conversaciones siguen en memoria de cada instancia de Lambda. Es trabajo de
código pendiente, no de infraestructura.

## Bloque F — Cognito y autorizador JWT

```
2026-10-15 | us-east-1 | cognito-idp:CreateUserPool | OK | grupo de usuarios tipo SPA; identificador de inicio de sesion = correo electronico; autorregistro DESHABILITADO (nadie en internet puede crearse cuenta); unico atributo obligatorio = email (minimizacion de datos)
2026-10-15 | us-east-1 | cognito-idp:DescribeUserPool | OK | dominio de inicio de sesion creado
2026-10-15 | us-east-1 | cognito-idp:DescribeUserPoolClient | OK | cliente PUBLICO sin secreto (ClientSecret ausente, verificado por longitud sin imprimir el valor); flujo OAuth = code (apto para PKCE en navegador)
2026-10-15 | us-east-1 | cognito-idp:UpdateUserPoolClient | OK | patron leer-modificar-escribir: se agrego la URL de retorno de Amplify y se quito el ambito phone en una sola pasada; ambitos resultantes = openid email
2026-10-15 | us-east-1 | cognito-idp:AdminCreateUser | OK | usuario de demo creado por administrador (el autorregistro esta deshabilitado); correo de invitacion SUPRIMIDO para no enviar nada a una direccion real; estado inicial FORCE_CHANGE_PASSWORD
2026-10-15 | us-east-1 | cognito-idp:AdminSetUserPassword | OK | contrasena definitiva (--permanent): evita que Cognito exija el cambio en pantalla durante la demo. Pedida por prompt con read -s: no queda en el historial del shell ni en ningun archivo
2026-10-15 | us-east-1 | cognito-idp:AdminGetUser | OK | UserStatus = CONFIRMED, Enabled = true
2026-10-15 | us-east-1 | apigatewayv2:CreateAuthorizer | OK | autorizador JWT con identity-source en la cabecera Authorization, audiencia = client id y emisor = el grupo de usuarios
2026-10-15 | us-east-1 | apigatewayv2:CreateRoute | OK | GET /healthz con AuthorizationType=NONE, para que el monitoreo no necesite credenciales
2026-10-15 | us-east-1 | verificacion de cierre | OK | GET /healthz -> 200; GET /api/v1/jardines sin token -> 401. La API ya NO acepta peticiones anonimas a rutas con datos
```

Un solo usuario de demo, con `email` como único atributo. Ningún dato de familias en el
directorio de usuarios. Ámbitos solicitados por el frontend: `openid email` (PREG-032); no
se pide `phone` porque nunca se recoge un teléfono.

## Bloque G — Amplify Hosting

```
2026-10-15 | us-east-1 | npm ci (frontend) | OK | 621 paquetes, 0 vulnerabilidades
2026-10-15 | us-east-1 | npm run build (frontend) | OK | build en 1,79 s; service worker PWA con 40 entradas en precache (860 KiB); copy canonico del Rol 4 desde content/ (BRUJULA_ALLOW_MOCK_COPY vacio, copySource CANONICAL, c4Status VALID)
2026-10-15 | us-east-1 | verificacion del bundle compilado | OK | la URL de la API en la nube y el emisor de Cognito quedaron congelados dentro del JS; MOCK_LOCAL ausente (0 coincidencias); literal SYNTHETIC_DEMO_NOT_A_REAL_PERSON presente
2026-10-15 | us-east-1 | Compress-Archive (PowerShell 5.1) sobre dist | FALLA | el zip quedo con 36 entradas con separador \ y 0 con /; Amplify (Linux) no reconoce assets/ y devuelve 404 en todo: index.html carga y la pagina queda EN BLANCO
2026-10-15 | us-east-1 | tar.exe -a -c -f sobre los hijos de dist | OK | zip de 0,23 MB con el CONTENIDO de dist en la raiz, separadores / y sin prefijo ./
2026-10-15 | us-east-1 | amplify: despliegue manual sin Git | OK | aplicacion y entorno creados por arrastre del zip; dominio HTTPS asignado (fuera del repo)
2026-10-15 | us-east-1 | amplify: reglas de reescritura | OK | Amplify creo sola /<*> -> /index.html tipo 404 Rewrite; no se agrego ni modifico ninguna regla
```

## Bloque D-ter — recreación del HTTP API por el preflight CORS

La primera HTTP API se creó con el atajo `create-api --target`, que genera una ruta
`$default` y una integración marcadas `ApiGatewayManaged=True`. Esos recursos no se pueden
borrar, y con `$default` presente el preflight CORS nunca funciona. Hubo que recrear la API
declarando cada recurso. Detalle y receta en el hallazgo 1.

```
2026-10-15 | us-east-1 | apigatewayv2:DeleteRoute sobre $default administrada | FALLA | la operacion responde sin error y get-routes sigue mostrando la ruta (ApiGatewayManaged=True no se borra)
2026-10-15 | us-east-1 | OPTIONS /api/v1/jardines con $default + autorizador JWT | FALLA | 401: el preflight no lleva token por definicion, coincide con $default y el autorizador lo rechaza; el navegador aborta y el frontend lo muestra como "No hay conexion"
2026-10-15 | us-east-1 | OPTIONS /api/v1/jardines con $default sin autorizador | FALLA | 405: el preflight llega a la Lambda y FastAPI no tiene CORS propio ni define OPTIONS. Las cabeceras access-control-* del gateway viajan, pero el status invalida el preflight
2026-10-15 | us-east-1 | apigatewayv2:CreateApi sin --target, con cors-configuration | OK | AllowOrigins = [<dominioAmplify>, http://localhost:4173], AllowMethods = GET/POST/OPTIONS, AllowHeaders = authorization/content-type, MaxAge 600
2026-10-15 | us-east-1 | apigatewayv2:CreateIntegration | OK | AWS_PROXY, payload-format-version 2.0, apuntando a la funcion brujula-api
2026-10-15 | us-east-1 | apigatewayv2:CreateAuthorizer | OK | JWT, identity-source $request.header.Authorization, audiencia <clientId>, emisor del grupo de usuarios
2026-10-15 | us-east-1 | apigatewayv2:CreateRoute | OK | GET /{proxy+} y POST /{proxy+} con AuthorizationType=JWT; GET /healthz con NONE. Ninguna ruta coincide con OPTIONS
2026-10-15 | us-east-1 | apigatewayv2:CreateStage | OK | etapa $default con AutoDeploy
2026-10-15 | us-east-1 | lambda:AddPermission | OK | invocacion autorizada a apigateway.amazonaws.com, acotada al id de la API nueva
2026-10-15 | us-east-1 | OPTIONS /api/v1/jardines (API nueva) | OK | 204 con access-control-allow-origin = <dominioAmplify>: el gateway responde el preflight el mismo, sin pasar por la Lambda
2026-10-15 | us-east-1 | GET /api/v1/jardines sin token (API nueva) | OK | 401 esperado: la ruta con datos sigue protegida
2026-10-15 | us-east-1 | GET /healthz (API nueva) | OK | 200
2026-10-15 | us-east-1 | apigatewayv2:GetRoutes (API nueva) | OK | tres rutas, todas con ApiGatewayManaged=None: GET /{proxy+} JWT, POST /{proxy+} JWT, GET /healthz NONE
```

Dos cosas que esta medición **no** cierra, y que PREG-032 sigue pidiendo: no se midió con
`-i` si la respuesta 401 del autorizador trae `Access-Control-Allow-Origin`, y el
`AllowHeaders` de la configuración quedó en `authorization, content-type`, **sin
`Idempotency-Key`**, que la PWA manda al registrar una conversación: ese POST fallaría el
preflight desde el navegador.

## Bloques no ejecutados

```
Bloque C — BedrockProvider | implementado en codigo, sin verificar contra la cuenta: el runtime corre con E3_LLM_PROVIDER=stub
Bloque H — retencion de CloudWatch | los logs de la Lambda llegan; falta put-retention-policy
```

## Cinco hallazgos operativos

Esto es el valor transferible del día: cada uno costó una vuelta completa y cada uno se
repite si alguien rehace el despliegue sin leerlo.

### 1. La HTTP API se crea sin `--target`, o el preflight CORS no funciona

**Síntoma.** El frontend en Amplify dice "No hay conexión" aunque la API responda. El
preflight `OPTIONS` devuelve 401 (o 405 si se le quita el autorizador a `$default`).

**Causa.** `aws apigatewayv2 create-api --target <arn>` es un atajo: crea una ruta
`$default` y una integración con `ApiGatewayManaged=True`. **Esos recursos no se pueden
borrar**: `delete-route` responde sin error y `get-routes` sigue mostrándola. Con `$default`
presente, el preflight —que por definición no lleva token— coincide con esa ruta y el
autorizador JWT lo rechaza con 401; el navegador aborta la petición real. Quitarle el
autorizador a `$default` tampoco sirve: el preflight llega entonces a la Lambda y FastAPI,
que no trae CORS propio ni define `OPTIONS`, responde 405. Las cabeceras `access-control-*`
del gateway viajan igual, pero un preflight con status 405 es un preflight fallido.

**Qué hacer.** Crear la API **sin** `--target` y declarar cada pieza: `create-api` con
`--cors-configuration`, `create-integration` (`AWS_PROXY`, formato 2.0),
`create-authorizer` (JWT), `create-route` para `GET /{proxy+}` y `POST /{proxy+}` con JWT y
para `GET /healthz` con `NONE`, y `create-stage --stage-name '$default' --auto-deploy`.
Después `lambda add-permission` acotado al id de la API nueva. Así ninguna ruta coincide con
`OPTIONS` y API Gateway contesta el preflight por su cuenta. Medido: **204** con
`access-control-allow-origin` correcto, **401** en ruta con datos sin token y **200** en
`healthz`. Si la API vieja ya existe, es más rápido crear una nueva que pelear con
`$default`.

### 2. El zip del frontend se arma con `tar`, no con `Compress-Archive`

**Síntoma.** Amplify sirve `index.html` y la página queda **en blanco**. Todos los assets
dan 404.

**Causa.** `Compress-Archive` de PowerShell 5.1 escribe los separadores de ruta con barra
invertida de Windows. El formato ZIP exige barra normal. Amplify corre sobre Linux y no
reconoce la carpeta `assets/`. Verificado: 36 entradas con `\` y 0 con `/`.

**Qué hacer.** Usar `tar.exe -a -c -f <zip> <hijos de dist>`, que viene con Windows 10 y 11.
Dos detalles que también rompen el despliegue: hay que empaquetar el **contenido** de `dist`
(no la carpeta, o Amplify responde "Access Denied") y sin prefijo `./`.

### 3. La regla de reescritura SPA la pone Amplify, y no hay que cambiarla

Amplify agrega sola `/<*>` → `/index.html` de tipo **404 Rewrite** para aplicaciones de una
sola página. No hay que crearla. Y **no conviene** cambiarla a `200 Rewrite` con ese mismo
origen: se aplicaría también a los assets reales y volvería a dejar la pantalla en blanco.
Consecuencia aceptada: las rutas internas responden con código 404 aunque entreguen la
página correcta, y el navegador la renderiza igual.

### 4. `admin-create-user` deja al usuario en `FORCE_CHANGE_PASSWORD`

**Síntoma.** El usuario de demo tendría que cambiar la contraseña en pantalla en medio de la
demostración.

**Qué hacer.** Seguir `cognito-idp admin-create-user` con `cognito-idp
admin-set-user-password --permanent`. La contraseña se pide por `read -s` para que no quede
en el historial del shell, y no se anota en ningún archivo. Verificar con `admin-get-user`:
`UserStatus = CONFIRMED`.

### 5. `update-user-pool-client` reemplaza la configuración completa

**Síntoma.** Agregar una URL de retorno borra los ámbitos, o al revés. Lo que no se le pasa
al comando se resetea.

**Qué hacer.** Patrón leer-modificar-escribir: `describe-user-pool-client` a un archivo,
modificar solo lo necesario y `update-user-pool-client --cli-input-json file://<archivo>`.
Así se agregó la URL de retorno de Amplify y se quitó el ámbito `phone` en una sola pasada,
sin perder nada más. Vale la misma precaución para cualquier `update-*` de Cognito.

## Lo que sigue sin verificar

Nada de esto está probado. No se declara hecho en ningún documento.

1. **La Lambda corre código anterior** a los PR #20, #21, #22, #24 y #26. Falta reconstruir
   el zip desde `main` y hacer `update-function-code`.
2. **Bedrock está apagado en runtime:** el código está conectado, pero la función corre con
   `E3_LLM_PROVIDER=stub`. El bloque C no se ejecutó contra la cuenta.
3. **DynamoDB no la usa el runtime.** La tabla existe y el TTL está confirmado, pero la
   caché de textos y el registro de conversaciones siguen en memoria de cada instancia.
4. **Retención de CloudWatch sin fijar** (bloque H): los logs llegan, falta
   `put-retention-policy`.
5. **No se midió el extremo a extremo** con inicio de sesión real de un usuario en el
   navegador: ni el login con PKCE, ni el token en una petición con datos, ni el logout.
6. **No se midió si el 401 del autorizador trae `Access-Control-Allow-Origin`** (PREG-032),
   y falta agregar `Idempotency-Key` al `AllowHeaders` del CORS antes de probar el POST de
   conversaciones desde el navegador.
7. **El alcance del rol del escritorio Kiro sigue sin probar.** La guía del equipo preguntaba
   si ese rol alcanzaba para DynamoDB, API Gateway, Cognito y Amplify. Esta bitácora **no lo
   responde**: lo verificado es el alcance de la identidad de CloudShell, que sí sirvió para
   todo, incluida la creación de roles de IAM. La recomendación operativa es trabajar en
   CloudShell (DEC-090) y no abrir el escritorio.
8. **Fuera del núcleo:** Step Functions, EventBridge, Glue, Athena, QuickSight, Kendra,
   OpenSearch, S3 Vectors, AgentCore, Macie, Textract, Polly, Translate, Transcribe, X-Ray,
   KMS, Secrets Manager, CDK, Budgets y CloudFront + WAF siguen `NO_VERIFICADO` y no se
   construyen para la Demo.
