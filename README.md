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
