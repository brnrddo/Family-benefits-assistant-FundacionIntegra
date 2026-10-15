# Despliegue alternativo (Docker) — NO es la vía oficial

> **Vía oficial de despliegue: zip + Mangum en AWS Lambda** (ver guía del Rol 2).
> Lo que hay en esta carpeta es una **alternativa de referencia / plan B**, no
> el camino que el equipo usa para la demo. No lo mezcles con la vía oficial:
> tener dos pipelines de despliegue en paralelo genera ambigüedad sobre cuál es
> el bueno.

## Cuándo usar esto

Solo si la vía zip+Mangum topa con un bloqueo, p. ej.:

- el artefacto zip supera el límite de Lambda (250 MB descomprimido), o
- hace falta fijar el intérprete exacto / dependencias del SO que el zip no
  reproduce.

En ese caso, esta imagen Docker ya está **verificada de punta a punta**
(Python 3.14.5-slim + uv, pipeline `make data` embebido, aserción de 10.000
evaluaciones en build-time) y sirve como respaldo inmediato.

## Cómo construir (si se necesita)

El contexto de build es la **raíz del repo** (el loader lee `data/publico/`):

```bash
# desde la raíz del repo:
docker build -f docs/deploy-alternativo/Dockerfile -t e3-backend .

# smoke test:
docker run --rm e3-backend
# -> evaluaciones: 10000 / accesos: 10000 / vistas listas: ...
```

> La generación de `e3.db` (loader + precálculo) NO depende de Docker: vive en
> `backend/Makefile` / `backend/make.ps1` (`make data`). La vía oficial zip
> reutiliza ese mismo pipeline para embeber la base en el artefacto Lambda.
