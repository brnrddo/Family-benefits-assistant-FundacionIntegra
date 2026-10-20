# Estructura del repositorio

La organización es por componentes con ownership funcional. No se crean carpetas personales ni scaffolding hasta elegir la tecnología que se implementará.

## Árbol objetivo

```text
.
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── README.md
├── backend/
│   └── README.md
├── frontend/
│   └── README.md
├── database/
│   └── README.md
├── ia/
│   └── README.md
├── data/
│   ├── README.md
│   ├── diccionario_datos.md
│   ├── distribucion.md
│   ├── ejemplos.md
│   ├── MANIFEST_PARTICIPANTES.sha256
│   ├── generador.py
│   ├── validador.py
│   └── publico/
│       ├── accesos_previos_causantes.csv
│       ├── accesos_previos_hogar.csv
│       ├── antecedentes_familia.csv
│       ├── beneficios.csv
│       ├── beneficios_fuentes.csv
│       ├── beneficios_versiones.csv
│       ├── comunas.csv
│       ├── condiciones_integrante.csv
│       ├── dataset_e3.json
│       ├── familias.csv
│       ├── fuentes.csv
│       ├── integrantes.csv
│       ├── jardines.csv
│       ├── pagos_beneficios.csv
│       ├── parametros_fuentes.csv
│       ├── parametros_version.csv
│       ├── postulaciones.csv
│       ├── postulaciones_causantes.csv
│       ├── postulaciones_estados.csv
│       ├── reglas_elegibilidad.csv
│       ├── reglas_fuentes.csv
│       ├── relaciones_integrantes.csv
│       ├── rsh_historial.csv
│       └── versiones_fuentes.csv
└── docs/
    ├── especificacion/
    │   └── PROYECTO_3_ESPECIFICACION_v2.md
    ├── equipo/
    │   └── ROLES_Y_RESPONSABILIDADES.md
    ├── arquitectura/
    │   └── ESTRUCTURA_REPOSITORIO.md
    └── producto/
        └── FLUJO_DE_FICHA.md
```

`.agents/` puede existir localmente para planes e informes del entorno, pero está ignorado por Git y no es documentación pública.

## Componentes y ownership

| Ruta | Finalidad | Dueño | Colaboradores |
|---|---|---|---|
| `backend/` | Motor determinista, API y coordinación técnica | Ingeniería en Computación | Mecánica entrega datos, características, acceso, prioridad y QA |
| `frontend/` | PWA mobile-first e integración | Ingeniería Eléctrica | Computación entrega API; Recursos Naturales valida UX |
| `database/` | Esquema, vistas y migraciones de la base derivada | Ingeniería Mecánica | Computación consume el contrato |
| `ia/` | Única integración Bedrock, prompts técnicos y filtro de contexto previo al envío | Ingeniería en Computación | Recursos Naturales revisa lenguaje y privacidad |
| `data/` | Fuente canónica sintética y sus herramientas | Ingeniería Mecánica | Computación consume datos sin cambiar su significado |
| `docs/especificacion/` | Fuente de verdad del alcance | Ingeniería en Computación coordina | Todo el equipo valida |
| `docs/equipo/` | Roles, handoffs y rutina | Todo el equipo | Liderazgo técnico mantiene coherencia |
| `docs/producto/` | Flujo, dominio, lenguaje y pruebas | Ingeniería en Recursos Naturales | Eléctrica y Computación validan viabilidad |
| `docs/arquitectura/` | Límites, contratos y decisiones técnicas | Ingeniería en Computación | Mecánica y Eléctrica |

El detalle de entregables está en [Roles y responsabilidades](ROLES_Y_RESPONSABILIDADES.md).

## Dónde crear archivos

- Código del servidor, motor y endpoints: `backend/` cuando se seleccione el stack; no incluye adaptadores ni prompts de Bedrock.
- Código de la PWA, recursos visuales y pruebas de interfaz: `frontend/`.
- Esquemas, migraciones y vistas: `database/`; no guardar bases locales ni dumps.
- Adaptadores de Bedrock, prompts técnicos y el único filtro de contexto previo al envío: `ia/`; los textos de producto se acuerdan con Recursos Naturales.
- Decisiones de producto y guiones de prueba: `docs/producto/`.
- Contratos técnicos y diagramas: `docs/arquitectura/`.
- Datos entregados: `data/publico/`; los 23 CSV son la fuente canónica.

`data/publico/dataset_e3.json` es útil para inspección o mocks, pero no sustituye los CSV: omite `data/publico/condiciones_integrante.csv`. Una base derivada debe poder reconstruirse relacionando los CSV.

## Límites obligatorios

1. Elegibilidad, estado de acceso y prioridad se calculan de forma determinista. Bedrock solo redacta explicaciones, guiones y mensajes usando resultados ya calculados y contexto filtrado.
2. No se envían a Bedrock nombres, RUT, folios RSH, teléfonos, nacionalidad, diagnósticos, salud ni antecedentes judiciales.
3. No se crean carpetas personales. El trabajo se asigna por componente y tarea.
4. No se versionan secretos, `.env`, credenciales, bases locales, dumps, datos reales ni artefactos pesados.
5. No se agregan CSV derivados como reemplazo de la fuente canónica. Los derivados deben ser reproducibles y vivir fuera de `data/publico/`.
6. No se crea código ficticio, archivos vacíos ni scaffolding antes de que el equipo elija framework y runtime.
7. Una configuración futura va en la raíz solo si una herramienta la exige globalmente; si pertenece a un componente, vive dentro de ese componente.
8. `.agents/` permanece local e ignorado; sus informes no se copian a documentación pública.

No se crea `CODEOWNERS` todavía. Será un paso futuro cuando estén definidos los usuarios de GitHub; entonces reflejará el ownership documentado aquí.
