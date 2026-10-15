#!/usr/bin/env bash
#
# Empaqueta el backend (FastAPI + Mangum) en brujula-api.zip para AWS Lambda.
#
# Via oficial del equipo: zip + Mangum. El Dockerfile es el plan B y vive en
# docs/deploy-alternativo/ (no lo usa este script).
#
# Se ejecuta en el escritorio Ubuntu del evento (AWS CLI, Python, rol IAM).
# NO llama a AWS: solo construye el artefacto, asi que puede correrse en
# cualquier maquina sin tocar la cuenta del evento.
#
# Uso (desde cualquier directorio):
#     bash backend/deploy/build_lambda.sh
#
# Variables opcionales (todas con default):
#     PY_VERSION=3.12                  version objetivo de los wheels
#     PLATAFORMA=manylinux2014_x86_64  arquitectura de los wheels
#     PYTHON_BIN=python3               interprete que corre pip
#     DIR_BUILD=<raiz>/build           directorio de staging (se BORRA)
#     ZIP_SALIDA=<raiz>/brujula-api.zip
#
# Detalle importante: el zip NO es "la carpeta backend comprimida". El backend
# lee archivos que viven fuera de backend/ (contrato C3, schemas C4, bundle de
# contenido) por rutas derivadas de __file__, asi que el zip reproduce el layout
# de la raiz del repo. Si ese layout se rompe, la Lambda falla al importar o
# degrada a mocks en silencio.
set -euo pipefail

# ---------------------------------------------------------------------------
# Preambulo
# ---------------------------------------------------------------------------
DIR_SCRIPT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
RAIZ_REPO="$(cd -- "$DIR_SCRIPT/../.." && pwd -P)"

morir() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

paso() {
    printf '\n[%s/6] %s\n' "$1" "$2"
}

# Resuelve una ruta (relativa o absoluta) contra el directorio actual. Exige
# que el directorio padre exista, para no crear staging en sitios raros.
ruta_absoluta() {
    local ruta="$1" dir base
    dir="$(dirname -- "$ruta")"
    base="$(basename -- "$ruta")"
    dir="$(cd -- "$dir" 2>/dev/null && pwd -P)" || morir "no existe el directorio de '$ruta'"
    printf '%s/%s\n' "$dir" "$base"
}

en_lista() {
    local aguja="$1" item
    shift
    for item in "$@"; do
        if [[ "$item" == "$aguja" ]]; then
            return 0
        fi
    done
    return 1
}

PY_VERSION="${PY_VERSION:-3.12}"
PLATAFORMA="${PLATAFORMA:-manylinux2014_x86_64}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DIR_BUILD="$(ruta_absoluta "${DIR_BUILD:-$RAIZ_REPO/build}")"
ZIP_SALIDA="$(ruta_absoluta "${ZIP_SALIDA:-$RAIZ_REPO/brujula-api.zip}")"

# Allowlist positiva de lo que se copia de backend/ (PRIVACIDAD_DEMO: incluir
# por lista explicita, nunca copiar todo y borrar despues).
PAQUETES_BACKEND=(app fixtures)

# Lo que a sabiendas NO va al zip. Si aparece un directorio nuevo que no esta
# ni aqui ni arriba, el script falla cerrado en vez de omitirlo en silencio.
IGNORADOS=(tests deploy .venv venv env .pytest_cache .ruff_cache .mypy_cache __pycache__)

# Herramientas de linea de comandos que el script usa.
HERRAMIENTAS=(zip find du awk)

# Rutas que el backend lee en runtime: tienen que existir en el repo Y en el
# staging, con exactamente esta forma relativa.
RUTAS_REQUERIDAS=(
    backend/app/api/app.py
    backend/app/config.py
    backend/fixtures/c4_mock/manifest.json
    .kiro/specs/_shared/contracts/C3-api.openapi.yaml
    .kiro/specs/_shared/contracts/C4-contenido-manifest.schema.json
    .kiro/specs/_shared/contracts/schemas/LlmContextV1.schema.json
    .kiro/specs/_shared/contracts/schemas/FamilyGenerationRequestV1.schema.json
    content/manifest.yaml
)

# Archivos que necesita el build pero que NO viajan en el zip.
INSUMOS_BUILD=(
    backend/requirements.txt
    backend/requirements-lambda.txt
    backend/deploy/lambda_function.py
)

# Lo que jamas puede quedar dentro del staging (datos, secretos, dataset).
GLOBS_PROHIBIDOS=('*.db' '*.sqlite' '*.sqlite3' '*.pem' '*.key' '.env' '.env.*')
DIRS_PROHIBIDOS=(backend/tests backend/.venv backend/deploy data)

# El escaneo de GLOBS_PROHIBIDOS se limita a lo que copiamos del repo: las
# dependencias de PyPI traen archivos legitimos con esas extensiones (botocore
# incluye su propio cacert.pem) y no son material nuestro.
DIRS_ESCANEADOS=(backend content .kiro)

# 50 MB: tope de Lambda para subir el zip directo en la llamada a la API.
LIMITE_SUBIDA_DIRECTA=52428800
# 250 MB descomprimidos es el tope del paquete; avisamos antes de llegar.
LIMITE_DESCOMPRIMIDO_MB=240

printf 'Empaquetado Lambda (zip + Mangum)\n'
printf '  raiz del repo : %s\n' "$RAIZ_REPO"
printf '  staging       : %s\n' "$DIR_BUILD"
printf '  zip de salida : %s\n' "$ZIP_SALIDA"
printf '  objetivo      : python%s / %s\n' "$PY_VERSION" "$PLATAFORMA"

# ---------------------------------------------------------------------------
paso 1 "comprobaciones previas"
# ---------------------------------------------------------------------------
if [[ ! -f "$RAIZ_REPO/backend/app/api/app.py" ]]; then
    morir "no encuentro la raiz del repo desde '$DIR_SCRIPT'; este script debe vivir en backend/deploy/"
fi

# El staging se borra con rm -rf: no puede apuntar a codigo del repo.
case "$DIR_BUILD" in
    "$RAIZ_REPO")
        morir "DIR_BUILD no puede ser la raiz del repo: el script borra ese directorio"
        ;;
    "$RAIZ_REPO"/backend* | "$RAIZ_REPO"/content* | "$RAIZ_REPO"/.kiro* | "$RAIZ_REPO"/frontend* | "$RAIZ_REPO"/data*)
        morir "DIR_BUILD no puede quedar dentro de backend/, content/, .kiro/, frontend/ ni data/: el script borra ese directorio"
        ;;
esac

for herramienta in "${HERRAMIENTAS[@]}"; do
    if ! command -v "$herramienta" >/dev/null 2>&1; then
        morir "falta '$herramienta' en el PATH. En Ubuntu: sudo apt-get install -y zip coreutils gawk"
    fi
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    morir "no encuentro el interprete '$PYTHON_BIN'. Exportalo con PYTHON_BIN=<interprete>"
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    morir "'$PYTHON_BIN' no tiene pip. En Ubuntu: sudo apt-get install -y python3-pip"
fi

for rel in "${RUTAS_REQUERIDAS[@]}"; do
    if [[ ! -e "$RAIZ_REPO/$rel" ]]; then
        morir "falta $rel: el backend la lee en runtime; sin ella la Lambda no arranca o degrada a mocks"
    fi
done

for rel in "${INSUMOS_BUILD[@]}"; do
    if [[ ! -f "$RAIZ_REPO/$rel" ]]; then
        morir "falta $rel: es insumo del build"
    fi
done

# Guardia de la allowlist: ningun directorio de backend/ sin clasificar.
while IFS= read -r dir; do
    nombre="$(basename -- "$dir")"
    if ! en_lista "$nombre" "${PAQUETES_BACKEND[@]}" && ! en_lista "$nombre" "${IGNORADOS[@]}"; then
        morir "backend/$nombre no esta clasificado: agregalo a PAQUETES_BACKEND (va al zip) o a IGNORADOS (no va)"
    fi
done < <(find "$RAIZ_REPO/backend" -mindepth 1 -maxdepth 1 -type d)

printf '  ok: herramientas, rutas de runtime e insumos presentes\n'

# ---------------------------------------------------------------------------
paso 2 "limpiar staging y zip previo"
# ---------------------------------------------------------------------------
rm -rf "$DIR_BUILD"
# Imprescindible: 'zip -r' AGREGA a un zip existente, no lo reemplaza. Sin esto
# un build viejo se queda pegado dentro del nuevo.
rm -f "$ZIP_SALIDA"
mkdir -p "$DIR_BUILD/backend" "$DIR_BUILD/.kiro/specs/_shared"
printf '  ok: %s vacio\n' "$DIR_BUILD"

# ---------------------------------------------------------------------------
paso 3 "dependencias (wheels Linux, sin compilar nada local)"
# ---------------------------------------------------------------------------
# --platform/--implementation/--python-version: baja los wheels del Linux de
#   Lambda, no los de la maquina donde corre el script.
# --only-binary=:all:  pip lo exige junto con --platform y evita compilar.
# --no-compile         los .pyc de otra version de Python son peso muerto.
if ! "$PYTHON_BIN" -m pip install \
    --quiet \
    --no-compile \
    --target "$DIR_BUILD" \
    --platform "$PLATAFORMA" \
    --implementation cp \
    --python-version "$PY_VERSION" \
    --only-binary=:all: \
    -r "$RAIZ_REPO/backend/requirements-lambda.txt"; then
    morir "pip no pudo resolver wheels para cp${PY_VERSION}/${PLATAFORMA}; revisa PY_VERSION, la red o backend/requirements-lambda.txt"
fi
printf '  ok: dependencias instaladas desde backend/requirements-lambda.txt\n'

# ---------------------------------------------------------------------------
paso 4 "codigo propio, contratos y contenido"
# ---------------------------------------------------------------------------
for paquete in "${PAQUETES_BACKEND[@]}"; do
    cp -r "$RAIZ_REPO/backend/$paquete" "$DIR_BUILD/backend/$paquete"
done

# El contrato C3 se lee AL IMPORTAR app.api.app: sin estos archivos la Lambda
# no llega ni a /healthz.
cp -r "$RAIZ_REPO/.kiro/specs/_shared/contracts" "$DIR_BUILD/.kiro/specs/_shared/contracts"

# Bundle C4 del Rol 4. No es configurable por variable: lo fija este layout
# (content/ hermano de backend/ en la raiz del paquete).
cp -r "$RAIZ_REPO/content" "$DIR_BUILD/content"

# El entrypoint va en la RAIZ del zip: --handler lambda_function.handler
cp "$DIR_SCRIPT/lambda_function.py" "$DIR_BUILD/lambda_function.py"

find "$DIR_BUILD" -name __pycache__ -type d -prune -exec rm -rf {} +
find "$DIR_BUILD" -name '*.pyc' -type f -delete
printf '  ok: backend/{%s}, contratos, content/ y lambda_function.py copiados\n' "$(IFS=,; echo "${PAQUETES_BACKEND[*]}")"

# ---------------------------------------------------------------------------
paso 5 "verificar el staging antes de comprimir"
# ---------------------------------------------------------------------------
for rel in "${RUTAS_REQUERIDAS[@]}" lambda_function.py; do
    if [[ ! -e "$DIR_BUILD/$rel" ]]; then
        morir "el staging quedo sin $rel: revisa PAQUETES_BACKEND y los cp del paso 4"
    fi
done

for rel in "${DIRS_PROHIBIDOS[@]}"; do
    if [[ -e "$DIR_BUILD/$rel" ]]; then
        morir "$rel no debe ir en el zip y aparecio en el staging"
    fi
done

# La SQLite baja de S3 a /tmp en el arranque en frio: ninguna .db viaja en el
# zip. Tampoco ningun .env ni material de credenciales (PRIVACIDAD_DEMO).
for rel in "${DIRS_ESCANEADOS[@]}"; do
    for glob in "${GLOBS_PROHIBIDOS[@]}"; do
        encontrado="$(find "$DIR_BUILD/$rel" -name "$glob" -print -quit)"
        if [[ -n "$encontrado" ]]; then
            morir "el staging contiene '$glob' en $rel ($encontrado): no puede ir en el zip"
        fi
    done
done
printf '  ok: estan las rutas de runtime; sin tests, sin .db, sin .env, sin dataset\n'

# ---------------------------------------------------------------------------
paso 6 "comprimir e informar"
# ---------------------------------------------------------------------------
# -X: sin metadata extra del sistema de archivos (zip mas reproducible).
if ! (cd "$DIR_BUILD" && zip -q -r -X "$ZIP_SALIDA" .); then
    morir "zip fallo al comprimir $DIR_BUILD"
fi
if [[ ! -f "$ZIP_SALIDA" ]]; then
    morir "el zip no se creo en $ZIP_SALIDA"
fi

BYTES_ZIP="$(wc -c <"$ZIP_SALIDA" | tr -d '[:space:]')"
MB_ZIP="$(awk -v b="$BYTES_ZIP" 'BEGIN { printf "%.1f", b / 1048576 }')"
MB_CRUDO="$(du -sm "$DIR_BUILD" | cut -f1)"

cat <<FIN

================================================================
 LISTO
================================================================
 zip            : $ZIP_SALIDA
 tamano         : ${MB_ZIP} MB comprimido / ${MB_CRUDO} MB descomprimido
 objetivo       : python${PY_VERSION} ${PLATAFORMA}

 Al crear o actualizar la funcion:
   --handler lambda_function.handler
   --runtime python${PY_VERSION}        (tiene que coincidir con PY_VERSION)
   --timeout 29                         (el HTTP API corta la integracion a 30 s)
   --memory-size 1024                   (mas memoria = mas CPU = snapshot mas rapido)

 Variables de entorno de la funcion (solo NOMBRES; los valores se ponen en la
 consola o en la CLI, nunca en el repo):
   E3_MOCK=0                 modo real; con 1 todo responde mock
   E3_DB_PATH=/tmp/e3.db     OBLIGATORIA: /tmp es el unico directorio escribible
   E3_DB_S3_BUCKET=<bucket>  bucket privado con la copia SINTETICA de la SQLite
   E3_LLM_PROVIDER=bedrock   o stub (plantillas locales, sin AWS)
   E3_BEDROCK_REGION=us-east-1
   E3_BEDROCK_MODEL_ID=<perfilDeInferencia>
   E3_GUARDRAIL_ID=<guardrailId>        sin Guardrail no se llama a Bedrock
   E3_GUARDRAIL_VERSION=<version>
   E3_CONTENT_MANIFEST       NO hace falta: el default ya resuelve en el zip

 El zip NO lleva e3.db: la Lambda la baja de <bucket>/snapshots/e3.db a /tmp en
 el arranque en frio. Tampoco lleva tests, dataset CSV ni .env.
 CORS se configura en el HTTP API: el backend no trae CORS propio.
FIN

if [[ "$BYTES_ZIP" -gt "$LIMITE_SUBIDA_DIRECTA" ]]; then
    cat <<'FIN'

 >>> AVISO: el zip pasa los 50 MB que Lambda acepta por subida directa.
     Subelo a S3 y referencialo:
       aws s3 cp brujula-api.zip s3://<bucket>/<key>
       aws lambda create-function ... --code S3Bucket=<bucket>,S3Key=<key>
       aws lambda update-function-code --function-name <funcion> \
           --s3-bucket <bucket> --s3-key <key>
FIN
fi

if [[ "$MB_CRUDO" -gt "$LIMITE_DESCOMPRIMIDO_MB" ]]; then
    printf '\n >>> AVISO: %s MB descomprimidos, cerca del tope de 250 MB del paquete.\n' "$MB_CRUDO"
fi

printf '\n'
