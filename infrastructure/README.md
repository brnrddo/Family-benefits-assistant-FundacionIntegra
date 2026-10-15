# infrastructure/ — Esbozo del pipeline de precálculo (API-T08)

> **ESTADO: ESBOZO (no desplegable tal cual).** Son plantillas comentadas para
> dimensionar el diff del precálculo paralelo con Step Functions Distributed Map.
> No reescribe el motor (M2/M3): lo envuelve. Lo único con cambio conceptual
> real es el **cupo global de BEN-018**, que no puede vivir dentro de una
> partición y por eso va en un stage aparte.

## Idea en una imagen

```
EventBridge (cron / evento)
        │
        ▼
 Step Functions (state machine)
        │
   ┌────┴───────────────────────────────────────────────┐
   │ 1) PrepararManifiesto   → escribe items.jsonl en S3 │  (lista de jardines)
   │                                                     │
   │ 2) Map (DISTRIBUTED)    → N child executions         │  ◄── paralelo real
   │      cada child = Lambda SnapshotPartitionBuilder    │
   │      procesa 1 jardín, escribe su partición a S3     │
   │      (NO evalúa BEN-018: cupo es global)             │
   │                                                     │
   │ 3) CupoBen018 (reduce)  → 1 Lambda, universo completo│  ◄── stage aparte
   │      rankea elegibles, marca SIN_CUPO, escribe a S3  │
   │                                                     │
   │ 4) ValidarSnapshot + SmokeTest                       │
   │                                                     │
   │ 5) ActivarSnapshot      → DynamoDB CONTROL/ACTIVE    │  (transaccional)
   └─────────────────────────────────────────────────────┘
```

## Por qué Distributed (y no Inline) Map

- **Inline Map**: tope de ~40 iteraciones concurrentes y comparte el payload de
  256 KB e historial del padre. Alcanza para la Demo (50 jardines) a duras penas.
- **Distributed Map**: hasta 10.000 child executions, **lee los ítems desde S3**
  (manifiesto), cada child con su propio historial. Necesario para "Escala"
  (1.200 jardines) y evita el límite de 256 KB. Nacer en Distributed.

## Qué NO cambia del backend

- `app/engine/evaluator.py::Evaluator.evaluar(...)` — intacto.
- `app/access/service.py::AccesoService.evaluar_familia(...)` — intacto
  (ya recibe `conn` por inyección).

## Qué cambia / se agrega

| Pieza | Tipo | Archivo |
|---|---|---|
| Manifiesto de jardines | **nuevo** | `lambdas/prepare_manifest.py` |
| Wrapper Lambda por jardín | **nuevo** | `lambdas/snapshot_partition_builder.py` |
| Cupo BEN-018: leer cupo vigente | **nuevo** | `lambdas/calcular_cupo.py` |
| Cupo BEN-018: ranking global → SIN_CUPO | **nuevo** (mueve lógica existente) | `lambdas/cupo_ben018.py` |
| Validar + smoke test + activar CONTROL/ACTIVE | **nuevo** | `lambdas/validar_snapshot.py` |
| State machine (Distributed Map + reduce + activar) | **nuevo (IaC)** | `cdk/precompute_stack.py` |
| Empaquetado del bundle de Lambda | **nuevo** | `build_lambda.py` |

### Árbol

```
infrastructure/
├── README.md
├── build_lambda.py                        # arma cdk/build/lambda/ (backend/app + handlers + e3.db)
├── .gitignore                             # ignora build/ y *.db
├── lambdas/
│   ├── prepare_manifest.py
│   ├── snapshot_partition_builder.py
│   ├── calcular_cupo.py
│   ├── cupo_ben018.py
│   └── validar_snapshot.py
└── cdk/
    ├── app.py
    ├── precompute_stack.py
    └── requirements.txt
```

## El punto del cupo BEN-018 (lo importante)

Hoy `AccesoService._familias_dentro_cupo()` recorre **todas** las familias y
corta en las primeras `cupo` (75). Si se particiona por jardín, ninguna
partición ve el universo → el ranking se rompe. Solución del esbozo:

1. El **Map** evalúa los 19 beneficios "por familia" y, para BEN-018, emite solo
   los *candidatos* (SI) con sus llaves de orden: `inseguridad`, `ingreso_pc`, `id`.
2. El stage **CupoBen018** (1 Lambda, lee todos los candidatos de S3) hace el
   ranking global y marca `SIN_CUPO`. Idéntico resultado al secuencial.

## Despliegue (cuando deje de ser esbozo)

```bash
# 0) generar e3.db + precálculo (igual que en local)
cd backend && python -m app.loader.load --force && python -m app.db.build_views

# 1) armar el bundle de las Lambdas (backend/app + handlers + e3.db)
cd ../infrastructure && python build_lambda.py

# 2) sintetizar / desplegar la infraestructura
cd cdk
pip install -r requirements.txt      # aws-cdk-lib, constructs
cdk synth                            # ver la plantilla CloudFormation
cdk deploy                           # requiere credenciales + cdk bootstrap
```
