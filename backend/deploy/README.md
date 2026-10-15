# Empaquetado para AWS Lambda (zip + Mangum)

Tres archivos, un solo propósito: construir `brujula-api.zip`, el artefacto que
se sube a una Lambda de Python para servir la API del backend detrás de un
**API Gateway HTTP API**.

| Archivo | Qué es |
|---|---|
| `build_lambda.sh` | el build: deja `brujula-api.zip` en la raíz del repo |
| `lambda_function.py` | el entrypoint que viaja en la raíz del zip (`--handler lambda_function.handler`) |
| `../requirements-lambda.txt` | dependencias solo-nube: `-r requirements.txt` + `mangum` |

**Vía oficial del equipo: zip + Mangum.** El `Dockerfile` queda como plan B en
`docs/deploy-alternativo/` y no participa de este flujo.

## 1. Qué hace, en corto

Lambda no corre un servidor: corre una función. El backend sí es un servidor
ASGI (FastAPI, que en local se levanta con uvicorn). **Mangum** es el traductor:
convierte el evento JSON del HTTP API en una petición FastAPI y la respuesta de
vuelta. El zip lleva tres cosas: las librerías, nuestro código y
`lambda_function.py`, que arma el objeto `handler`.

El zip **no es "la carpeta `backend/` comprimida"**. El backend lee archivos que
viven fuera de `backend/` por rutas derivadas de `__file__`, así que el paquete
reproduce el layout de la raíz del repo:

```
/var/task/
├── lambda_function.py          <- entrypoint (copiado desde backend/deploy/)
├── backend/app/ ...            <- el código
├── backend/fixtures/c4_mock/   <- bundle C4 mock (JSON) del Rol 2
├── .kiro/specs/_shared/contracts/   <- contrato C3 + schemas C4/LlmContextV1
├── content/                    <- bundle C4 real del Rol 4 (YAML/MD/CSV/JSON)
└── fastapi/ pydantic/ boto3/ … <- dependencias
```

Si ese layout se rompe, la Lambda **falla al importar** (el contrato C3 se lee al
importar `app.api.app`) o **degrada a mocks en silencio** (bundle C4).

## 2. Dónde se ejecuta

En el **escritorio Ubuntu del evento** (AWS CLI, Python, rol IAM). El script es
bash y baja wheels de Linux: en Windows se puede verificar la sintaxis, los
tests del repo y que el árbol copiado importe, pero **no** el `pip install
--platform manylinux2014_x86_64` ni el zip final ni el arranque en frío. Lo
verificado hasta hoy está en
`.agents/tasks/empaquetado-lambda-2026-10-15/verificacion.md`.

```bash
bash backend/deploy/build_lambda.sh      # desde cualquier directorio
```

Variables opcionales, todas con default: `PY_VERSION` (3.12), `PLATAFORMA`
(`manylinux2014_x86_64`), `PYTHON_BIN` (`python3`), `DIR_BUILD`
(`<raíz>/build`), `ZIP_SALIDA` (`<raíz>/brujula-api.zip`). Ni `build/` ni el zip
se versionan (`.gitignore`).

`PY_VERSION` tiene que coincidir con el `--runtime` de la función: los `.so`
compilados (`pydantic_core`, `rpds-py`) se bajan para una versión concreta de
CPython y no cargan en otra. El repo se prueba con Python 3.11 (`py -3.11 -m
pytest`), así que 3.12 se valida recién con el smoke test de la Lambda; si
fallara, la salida es `PY_VERSION=3.11` + `--runtime python3.11`.

## 3. Variables de entorno de la Lambda

El backend **no lee ningún `.env`** (no hay `python-dotenv`): solo `os.environ`.
En Lambda se fijan en "Environment variables". Nombres y defaults, nunca valores.

| Variable | Valor demo | Si falta |
|---|---|---|
| `E3_MOCK` | `0` | default `1`: todo responde mock sintético |
| `E3_DB_PATH` | `/tmp/e3.db` | **trampa**: busca `backend/e3.db` (read-only, inexistente) y degrada a mocks |
| `E3_DB_S3_BUCKET` | `<bucket>` | no se baja la SQLite; la API queda en mocks |
| `E3_LLM_PROVIDER` | `bedrock` | default `stub`: plantillas locales, sin AWS |
| `E3_BEDROCK_REGION` | `us-east-1` | default `us-east-1` (única región del evento) |
| `E3_BEDROCK_MODEL_ID` | `<perfilDeInferencia>` | default del código: perfil `us.*` de Claude Haiku |
| `E3_GUARDRAIL_ID` | `<guardrailId>` | con `E3_LLM_PROVIDER=bedrock` falla cerrado: sin Guardrail no se llama a Bedrock |
| `E3_GUARDRAIL_VERSION` | `<version>` | default `1` |
| `E3_CONTENT_MANIFEST` | **no tocar** | el default ya resuelve dentro del zip |

Tres advertencias que cuestan tiempo si se descubren en vivo:

- **`E3_DB_PATH=/tmp/e3.db` es obligatoria.** `/tmp` es el único directorio
  escribible del runtime.
- **`E3_CONTENT_MANIFEST` no hace falta y es asimétrica.** Solo afecta al mock
  JSON (`app/priority/config.cargar_ranking_config`), cuyo default
  `backend/fixtures/c4_mock/manifest.json` ya resuelve bien en el zip. El bundle
  **real** (`content/manifest.yaml`) **no es configurable por entorno**:
  `content_c4.CONTENT_MANIFEST` y `content_catalog.DEFAULT_MANIFEST` son
  constantes derivadas de `__file__`. Lo que lo fija es el layout del zip
  (`content/` hermano de `backend/`). Las dos variantes se usan a la vez: el
  mock para el chequeo de `warnings_runtime()`, el real para texto y datos.
- **`E3_LLM_PROVIDER=bedrock` y `E3_GUARDRAIL_*` se declaran pero hoy no tienen
  efecto en las rutas**: `BedrockProvider` existe y ninguna ruta lo invoca
  todavía.

## 4. Qué NO va en el zip

| Fuera | Por qué |
|---|---|
| `e3.db` | la SQLite (**sintética**) baja de `<bucket>/snapshots/e3.db` a `/tmp` en el arranque en frío |
| `backend/tests/` | no se ejecutan en la nube |
| `data/publico/` (CSV) | solo los usa el loader, y el loader no corre en la Lambda |
| `.venv/`, `__pycache__`, `*.pyc` | peso muerto; los `.pyc` serían de otra versión de Python |
| cualquier `.env`, `.pem`, `.key`, `*.db` | PRIVACIDAD_DEMO: el paso 5 del script falla si aparecen |

La copia es por **allowlist positiva** (`backend/app/`, `backend/fixtures/`), no
por "copiar todo y borrar después". Si alguien crea un directorio nuevo en
`backend/`, el script **se detiene** y pide clasificarlo: así la lista no se
queda obsoleta en silencio.

## 5. Pegar el zip en AWS

Con marcadores genéricos: nunca el número de cuenta, el nombre real del bucket
ni el id del Guardrail en el repo.

```bash
# zip de hasta 50 MB: subida directa
aws lambda create-function --function-name <funcion> \
  --runtime python3.12 --handler lambda_function.handler \
  --role arn:aws:iam::<cuenta>:role/<rol> \
  --timeout 29 --memory-size 1024 \
  --zip-file fileb://brujula-api.zip

# si pasa de 50 MB: por S3
aws s3 cp brujula-api.zip s3://<bucket>/<key>
aws lambda update-function-code --function-name <funcion> \
  --s3-bucket <bucket> --s3-key <key>
```

- `--timeout 29`: el HTTP API corta la integración a los 30 s. Un timeout mayor
  en la Lambda no sirve de nada y esconde el corte real.
- El rol necesita leer `<bucket>/snapshots/*` (y `bedrock:InvokeModel` +
  `bedrock:ApplyGuardrail` cuando se conecte el provider).
- **CORS se configura en el HTTP API**: el backend no trae middleware de CORS.
- El script imprime el tamaño del zip y el aviso de los 50 MB al terminar.

## 6. Trampas conocidas

1. **Hoy no hay autenticación.** `app/api/deps.py` concede todos los scopes
   cuando el cliente no manda el header `X-Demo-Scopes`. Detrás de un HTTP API
   público, eso es una API abierta a internet. Cognito sigue `NO_VERIFICADO`;
   decisión del equipo: montarlo o no publicar la URL. No se arregla desde acá.
2. **`lifespan="off"`** (obligatorio con Mangum) desactiva el precalentamiento
   del snapshot del motor: el **primer** request de datos paga ~4-5 s. Cabe en
   los 29 s, pero conviene invocar `/healthz` y una ruta de datos una vez
   después de desplegar.
3. **Antes de presentar, mirar CloudWatch**: `runtime_degradado_a_mock` y
   `e3_db_descarga_fallida` significan que la demo se ve bien **en mocks**. El
   entrypoint sube a INFO solo los loggers propios (el runtime deja el root en
   WARNING y el access log saneado se perdería).
4. **Si alguien agrega una lectura de archivos fuera de `backend/`**, hay que
   sumarla a `RUTAS_REQUERIDAS` en el script. Hoy son cinco sitios:
   `app/api/app.py` (C3, al importar), `app/priority/config.py` (schema C4),
   `app/priority/content_c4.py` (`content/manifest.yaml`),
   `app/genai/content_catalog.py` (mismo bundle) y `app/genai/llm_context.py`
   (`LlmContextV1.schema.json`).
5. **El `sha256` de C4 es sobre bytes, sin normalizar CRLF.** `content/` está
   fijado a LF (`content/.gitattributes`, DEC-045) y `cp` preserva bytes: no
   "arreglar" finales de línea al copiar o el bundle falla cerrado.

## 7. Estado AWS

| Componente | Estado |
|---|---|
| Bedrock Converse + Guardrails | probados en la cuenta del evento (us-east-1), registro aparte |
| Lambda, API Gateway HTTP API, S3, DynamoDB, Cognito, Amplify | `NO_VERIFICADO` en `docs/ARQUITECTURA_AWS.md` |
| este zip | **nunca construido ni desplegado todavía**: el build real corre en el escritorio del evento |

Sin números de cuenta, sin nombres de bucket, sin ids de Guardrail, sin
endpoints. Todos los datos de la demo son sintéticos.
