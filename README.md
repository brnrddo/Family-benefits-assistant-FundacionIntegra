# 🚀 AWS Breaking Barriers — Hackathon

Proyecto del equipo para el hackathon. Usamos **base de datos**, **frontend** e **IA generativa** sobre AWS.
Todos trabajamos desde **Kiro** (el editor con IA basado en VS Code).

---

## 📁 Estructura del proyecto

```
.
├── frontend/     # Interfaz de usuario (web)
├── backend/      # API y lógica del servidor
├── database/     # Esquemas, migraciones y scripts de la base de datos
├── ia/           # Prompts, integración con IA generativa (Bedrock / etc.)
├── .env.example  # Plantilla de variables de entorno (CÓPIALA, no la edites)
└── README.md
```

---

## 📊 Estado del proyecto por rol

> Resumen vivo para que cualquiera sepa qué está listo y qué sigue.

### 🗄️ Rol 1 · Datos y motor de elegibilidad — **MUST completo**
Backend en `backend/` (Python 3.11+, SQLite, solo stdlib para datos/motor).
Ver detalle y comandos en [`backend/README.md`](./backend/README.md).

- ✅ **M1** Loader: 23 CSV → `backend/e3.db` (500 familias, 1.700 integrantes, 20 beneficios, 41 versiones, 151 reglas).
- ✅ **M1** Vistas de cruce: `v_familia_beneficio`, `v_oportunidades`, `v_brechas`, `v_ventanas`.
- ✅ **Precálculo** persistido (tablas `evaluaciones` + `accesos`, 10.000 evaluaciones) en < 30 s.
- ✅ **M2** Motor de elegibilidad determinista con traza (SI/NO/INDETERMINADO · CONFIRMADO/PRELIMINAR).
- ✅ **M3** Estado de acceso (8 estados) + cupo BEN-018 (`SIN_CUPO`).
- ✅ **M3b** Ficha sintética + `contexto_familia` (contrato **C2**) + filtro de privacidad hacia el LLM.
- ✅ **Resiliencia** a datos mal ingresados: saneo + `inconsistencias` + `calidad_datos`.
- ✅ **Base GenAI** para el Rol 2: `app/genai/` con `LLMProvider`, `StubProvider` (sin AWS) y esqueleto `BedrockProvider`.
- ✅ Tests: **88 passed**, `ruff` limpio.

**Contratos que entrega a otros roles:**
- **C1** (salida del motor, §6.6): tabla `evaluaciones` / vista `v_familia_beneficio`.
- **C2** (`contexto_familia`, §2.7.2): `app/context/contexto_familia.py` → filtrar con `app/context/context_filter.filtrar_para_llm` antes de ir al LLM.

### ⚙️ Rol 2 · API, priorización e IA — pendiente
Toma como base: las vistas de cruce (C1), `contexto_familia` (C2) y `app/genai/` (rellenar `BedrockProvider`).

### 📱 Rol 3 · Frontend — pendiente
### 🎯 Rol 4 · Producto, contenido y pitch — pendiente (`content/` aún no creado)

---

## 🗺️ Esquema: cómo encaja el trabajo del Rol 1 (para el equipo)

Flujo de datos de punta a punta (spec §2.6). **Lo que ya está hecho (Rol 1) va
marcado con ✅; lo pendiente de otros roles con ⬜.**

```
  CSV del dataset E-3 (data/publico/, 23 archivos)
         │
         ▼
 ┌───────────────────────────────────────────────────────────┐
 │ [1] ✅ LOADER  (app/loader/load.py)                         │
 │     23 CSV ──► SQLite e3.db  (500 fam · 1.700 int · 20 ben) │
 └───────────────────────────────────────────────────────────┘
         │
         ▼
 ┌───────────────────────────────────────────────────────────┐
 │ [2] ✅ MOTOR DE ELEGIBILIDAD  (app/engine/)                 │
 │     ¿califica? → SI / NO / INDETERMINADO                    │
 │     nivel CONFIRMADO / PRELIMINAR + traza regla-por-regla   │
 │     → contrato C1                                           │
 └───────────────────────────────────────────────────────────┘
         │
         ▼
 ┌───────────────────────────────────────────────────────────┐
 │ [3] ✅ ESTADO DE ACCESO  (app/access/)                      │
 │     cruza elegibilidad + gestiones reales → 8 estados       │
 │     incl. ELEGIBLE_SIN_ASIGNACION (la brecha) y SIN_CUPO    │
 └───────────────────────────────────────────────────────────┘
         │
         ▼
 ┌───────────────────────────────────────────────────────────┐
 │ [4] ✅ VENTANA DE CONTEXTO  (app/context/)                  │
 │     ficha sintética + contexto_familia (C2) + sanitizer     │
 │     (resiliencia a datos sucios) + filtro de privacidad     │
 └───────────────────────────────────────────────────────────┘
         │
         ├─────────── PRECÁLCULO ✅ (app/db/build_views.py) ───────────┐
         │   tablas evaluaciones + accesos (10.000 filas, < 30 s)      │
         │   vistas: v_familia_beneficio · v_oportunidades ·           │
         │           v_brechas · v_ventanas                            │
         ▼                                                             │
 ┌──────────────────────────┐   ┌──────────────────────────────────┐  │
 │ [5] ⬜ PRIORIZACIÓN       │   │  ✅ BASE GENAI (app/genai/)       │  │
 │     U·B·V  (Rol 2)        │   │  LLMProvider + stub; Rol 2 pone   │  │
 │                           │   │  Bedrock (Claude). El LLM NO      │  │
 │                           │   │  decide elegibilidad.             │  │
 └──────────────────────────┘   └──────────────────────────────────┘  │
         │                                                             │
         ▼                                                             │
 ┌───────────────────────────────────────────────────────────┐        │
 │ [6] ⬜ VISTA DE LA TÍA (Rol 3) + API (Rol 2)               │◄───────┘
 │     "3 cosas para conversar" + guion IA + marcar conversado │
 └───────────────────────────────────────────────────────────┘
```

### ¿Qué consume cada rol de lo que entrega el Rol 1?

| Rol | Qué toma del Rol 1 | Cómo |
|---|---|---|
| **Rol 2** (API/priorización) | **C1** (elegibilidad + estado) | Lee la vista `v_familia_beneficio` (o `v_oportunidades`, `v_brechas`) por SQL. No necesita re-evaluar el motor. |
| **Rol 2** (eje Urgencia) | ventanas de inscripción | Vista `v_ventanas` (días a cierre + flag `ventana_discrimina`). Ojo caveat §8.1: mantener `usar_ventana=false` por defecto. |
| **Rol 2** (IA) | **C2** + base GenAI | `app/context/contexto_familia.py` → **filtrar con** `context_filter.filtrar_para_llm` antes del LLM. Implementar `BedrockProvider` en `app/genai/provider.py`. |
| **Rol 3** (frontend) | semáforo, chips, montos | Mismas vistas; cada fila trae `semaforo`, `estado_acceso`, `monto_estimado`, `requiere_accion_familia`, `canal`, `fuente_url`. |
| **Rol 4** (contenido) | campos de catálogo | `beneficios`, `fuentes` y `politica_perdida/advertencia` (ver `ROADMAP_ROL1.md` G5). |

### Contratos (congelados por el Rol 1)
- **C1** — salida del motor por (familia × beneficio): `resultado`, `nivel`,
  `motivos`, `datos_faltantes`, `entidad_ganadora`, `monto_estimado`, `traza`.
  → tabla `evaluaciones` / vista `v_familia_beneficio`.
- **C2** — `contexto_familia` (roles/edades, rsh.tramo, rango de ingreso,
  señales, inconsistencias, calidad_datos). → `app/context/contexto_familia.py`.
  Lo que puede ver el LLM lo decide **solo** `context_filter.filtrar_para_llm`.

### Qué falta / mejoras del Rol 1
Ver [`backend/ROADMAP_ROL1.md`](./backend/ROADMAP_ROL1.md): ganchos documentados
(bindings ACCESO para BEN-004, montos por fórmula/tramo, exponer política de
pérdida) con su utilidad y esfuerzo.

---

## ⚡ Backend en 30 segundos (Rol 1)

```bash
cd backend
python -m app.loader.load          # genera e3.db desde los CSV
python -m app.db.build_views       # precálculo + vistas de cruce (< 30 s)
pip install -r requirements-dev.txt
pytest                             # 88 tests
```

Nota: `e3.db` es efímera (no se versiona); se regenera con esos dos comandos.

---

## ✅ Primer día: cómo empezar (paso a paso)

> No hace falta saber usar la terminal. Casi todo se hace con botones dentro de Kiro.

### 1. Tener cuenta de GitHub
Si no tienes, créala gratis en https://github.com y pásale tu usuario a quien administra el repo para que te agregue como **colaborador**. Vas a recibir una invitación por correo: **acéptala**.

### 2. Clonar el proyecto en Kiro
1. Abre **Kiro**.
2. Pulsa `Ctrl + Shift + P` (Windows) o `Cmd + Shift + P` (Mac) para abrir la paleta de comandos.
3. Escribe **`Git: Clone`** y selecciónalo.
4. Pega esta URL cuando te la pida:
   ```
   https://github.com/brnrddo/Aws-breaking-barriers---10-
   ```
5. Elige una carpeta de tu computadora donde guardarlo.
6. La **primera vez** te pedirá iniciar sesión en GitHub: se abre el navegador, le das **"Authorize"** y listo. **Kiro guarda tus credenciales solo — no tienes que crear tokens ni nada.**

### 3. Preparar tus variables de entorno
1. Copia el archivo `.env.example` y renómbralo a `.env`.
2. Rellena los valores reales (claves de AWS, base de datos, etc.).
3. ⚠️ **El archivo `.env` NUNCA se sube a GitHub** (ya está protegido). Las claves se comparten por un canal privado (ej. mensaje directo), nunca por el repo.

---

## 🔄 Cómo trabajar día a día (flujo de siempre)

Para no pisarnos entre nosotros, repite estos 3 pasos **cada vez que te sientas a trabajar**:

| Paso | Qué hacer | Dónde en Kiro |
|------|-----------|----------------|
| 1️⃣ **Antes de empezar** | Traer los cambios de los demás (`Pull`) | Panel de **Source Control** → menú `...` → **Pull** |
| 2️⃣ **Mientras trabajas** | Guardar tus cambios (`Commit`) | Panel de **Source Control** → escribe un mensaje → **Commit** |
| 3️⃣ **Al terminar** | Subir tus cambios (`Push`) | Panel de **Source Control** → menú `...` → **Push** |

> 📌 **Regla de oro:** siempre **Pull antes de empezar** y **Push al terminar**. Así evitamos conflictos.

Más detalles y qué hacer si algo sale mal 👉 ver [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## 🔐 Reglas de seguridad (importantísimo en un hackathon)

- ❌ **Nunca** subas claves, contraseñas o el archivo `.env`.
- ❌ **Nunca** pegues una API key o secret dentro del código.
- ✅ Todo secreto va en tu `.env` local (protegido por `.gitignore`).
- ✅ Si vas a compartir una clave con el equipo, hazlo por mensaje privado, no por el repo.
- 🚨 Si por error subes un secreto, **avisa de inmediato** para rotar/invalidar esa clave.
