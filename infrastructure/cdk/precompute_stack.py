"""ESBOZO — Stack CDK del pipeline de precálculo (Step Functions Distributed Map).

NO desplegable tal cual: faltan credenciales, bootstrap y el empaquetado real
del código del backend como asset de Lambda. Sirve para dimensionar el diff IaC.

Flujo de la state machine:

  PrepararManifiesto (Lambda)
        │
        ▼
  Map  (DISTRIBUTED, ItemReader = manifiesto JSONL en S3)
        └── por jardín: SnapshotPartitionBuilder (Lambda)   ◄── paralelo real
        │
        ▼
  CalcularCupo (Lambda; lee cupo_contingente de la versión vigente)
        │
        ▼
  CupoBen018 (Lambda reduce; ranking global → SIN_CUPO)
        │
        ▼
  ValidarSnapshot + SmokeTest (Lambda)
        │
        ▼
  ActivarSnapshot (DynamoDB CONTROL/ACTIVE, transaccional condicional)

Para "Demo" (50 jardines) `max_concurrency` modesto; para "Escala" (1.200)
subirlo. Distributed Map admite hasta 10.000 child executions.
"""
from __future__ import annotations

from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class PrecomputeStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kwargs) -> None:
        super().__init__(scope, cid, **kwargs)

        # --- almacenamiento ------------------------------------------------
        bucket = s3.Bucket(
            self, "SnapshotBucket",
            versioned=True,
            enforce_ssl=True,
            removal_policy=None,  # ESBOZO: definir según entorno
        )

        control = dynamodb.Table(
            self, "ControlActive",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # --- código del backend como asset de Lambda ----------------------
        # La carpeta build/lambda la arma `infrastructure/build_lambda.py`:
        # copia backend/app + los handlers + e3.db (solo-lectura).
        # from_asset monta el código en /var/task, así que e3.db queda ahí.
        common_env = {
            "SNAPSHOT_BUCKET": bucket.bucket_name,
            "E3_DB_PATH": "/var/task/e3.db",
        }
        code = lambda_.Code.from_asset("build/lambda")

        def fn(name: str, handler_path: str, timeout_min: int = 2) -> lambda_.Function:
            f = lambda_.Function(
                self, name,
                runtime=lambda_.Runtime.PYTHON_3_12,   # 3.12+ habilita SnapStart
                handler=handler_path,
                code=code,
                memory_size=1024,
                timeout=Duration.minutes(timeout_min),
                environment=common_env,
            )
            bucket.grant_read_write(f)
            return f

        prepare = fn("PrepareManifest", "prepare_manifest.handler")
        builder = fn("SnapshotPartitionBuilder", "snapshot_partition_builder.handler", 5)
        calc_cupo = fn("CalcularCupo", "calcular_cupo.handler")
        cupo018 = fn("CupoBen018", "cupo_ben018.handler", 3)
        validar = fn("ValidarSnapshot", "validar_snapshot.handler")
        # El validador también activa CONTROL/ACTIVE: necesita la tabla y permisos.
        validar.add_environment("CONTROL_TABLE", control.table_name)
        control.grant_read_write_data(validar)

        # --- pasos ---------------------------------------------------------
        preparar = tasks.LambdaInvoke(
            self, "PrepararManifiesto",
            lambda_function=prepare,
            payload_response_only=True,
            result_path="$.manifest",
        )

        # Distributed Map: itera sobre el manifiesto JSONL en S3.
        mapa = sfn.DistributedMap(
            self, "MapPorJardin",
            max_concurrency=50,   # Demo; subir para Escala (hasta 10.000)
            item_reader=sfn.S3JsonItemReader(   # ESBOZO: usar reader JSONL real
                bucket=bucket,
                key=sfn.JsonPath.string_at("$.manifest.manifest_key"),
            ),
            result_writer=sfn.ResultWriter(
                bucket=bucket,
                prefix="map-results/",
            ),
        )
        mapa.item_processor(
            tasks.LambdaInvoke(
                self, "ProcesarJardin",
                lambda_function=builder,
                payload_response_only=True,
            )
        )

        calcular_cupo = tasks.LambdaInvoke(
            self, "CalcularCupo",
            lambda_function=calc_cupo,
            payload_response_only=True,
            result_path="$.cupo",
        )

        reducir_cupo = tasks.LambdaInvoke(
            self, "CupoBen018",
            lambda_function=cupo018,
            payload_response_only=True,
            result_path="$.ben018",
        )

        validar_snapshot = tasks.LambdaInvoke(
            self, "ValidarYActivar",   # valida, smoke test y activa CONTROL/ACTIVE
            lambda_function=validar,
            payload_response_only=True,
        )

        # --- encadenado ----------------------------------------------------
        definicion = (
            preparar
            .next(mapa)
            .next(calcular_cupo)
            .next(reducir_cupo)
            .next(validar_snapshot)
        )

        sfn.StateMachine(
            self, "PrecomputeStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definicion),
            timeout=Duration.minutes(30),   # objetivo plan Rol 1 (< 30 s de pared esperado)
        )

        # ESBOZO: EventBridge rule → start_execution para recálculo programado.
