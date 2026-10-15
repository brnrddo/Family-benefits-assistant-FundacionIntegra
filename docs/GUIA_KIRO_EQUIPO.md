# Guía Kiro para el equipo

Empiece siempre en el [índice de Specs](../.kiro/specs/INDICE.md). Esta guía distingue el baseline documental actual de la implementación futura: hoy los contratos y tareas existen, pero aplicación, infraestructura y pruebas aún no.

## 1. Elija modo y autonomía

| Necesidad | Modo | Ejemplo |
|---|---|---|
| pregunta, auditoría, gap pequeño o cambio de un archivo | **Vibe/Default** | comparar un diff con tres criterios sin editar |
| trabajo trazable con requisitos/diseño/tareas | **Spec** | implementar una tarea `API-T05` completa |
| tarea acotada, reversible y con validación clara | **Autopilot** | ajustar copy C4 y ejecutar validaciones existentes |
| contrato, privacidad, AWS, conflicto o decisión de producto | **Supervised** | cambiar C3, una allowlist o una topología cloud |

Use `#File` para dar un archivo exacto y `#Folder` para un área completa. Ejemplos:

```text
#File .kiro/specs/api-priorizacion-genai/requirements.md
#File .kiro/specs/_shared/contracts/C3-api.openapi.yaml
Implementa únicamente API-T01. No cambies C3; valida contra OpenAPI.
```

```text
#Folder frontend
#File .kiro/specs/frontend-pwa/tasks.md
Audita FE-T02 contra el código. Devuelve CONFORME/PARCIAL/DIVERGE/NO_VERIFICADO sin editar.
```

## 2. Ramas de workstream y ownership por componente

Los rótulos Rol 1–4 identifican workstreams de las Specs; no reemplazan el ownership humano por componente. La correspondencia autoritativa está en [DEC-022](../.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md#decisiones).

| Workstream | Rama | Spec | Componentes y aprobación |
|---|---|---|---|
| Rol 1 Datos/motor | `datos` | [triada](../.kiro/specs/datos-motor-elegibilidad/requirements.md) | Mecánica: `data/`, `database/`, loader/features/access/priority/context/QA; Computación: motor `backend/` |
| Rol 2 API/AWS | `api` | [triada](../.kiro/specs/api-priorizacion-genai/requirements.md) | Computación: `backend/`, `ia/` y arquitectura; Mecánica: priority; Eléctrica: infraestructura/despliegue |
| Rol 3 Front | `front` | [triada](../.kiro/specs/frontend-pwa/requirements.md) | Eléctrica: `frontend/` e integración visible |
| Rol 4 Contenido | `contenido` | [triada](../.kiro/specs/producto-contenido-demo/requirements.md) | Recursos Naturales: `docs/producto/`, `content/`, demo y pitch; sin Python/TypeScript |

El dueño del componente aprueba sus cambios. Ayudar desde otro workstream no transfiere ownership. Los contratos [C0–C4](../.kiro/specs/_shared/contracts/) se cambian coordinadamente, no desde una sola rama.

## 3. Rutina diaria para personas nuevas

1. Abra el índice y el spec de su rol: `requirements.md` → `design.md` → `tasks.md`.
2. Verifique que está en la rama del rol. Rol 2 trabaja en `api`.
3. Haga **Pull** del baseline aprobado como indica [`CONTRIBUTING.md`](../CONTRIBUTING.md), preservando cambios locales.
4. Elija la primera tarea no bloqueada y lea requisitos, contratos y dependencias citados.
5. Pida a Kiro el cambio mínimo dentro del ownership; no permita refactors ajenos.
6. Ejecute la validación existente indicada. No marque `[x]` sin evidencia real.
7. Actualice la matriz de estado, haga un commit pequeño y claro, y **Push** a su rama.
8. Abra PR para revisión humana. No integre directamente a `main`.

Los puntos diarios son: **10:00** acuerdos/contratos; **14:00** integrar lo disponible; **19:00** demo interna de cinco minutos. Si un bloqueo dura 30 minutos, acuerde un mock o adaptador temporal compatible; no cree un contrato paralelo.

## 4. Adopción retroactiva sin perder avances

Primero se integra un baseline solo documental revisado. Luego cada rama incorpora el baseline sin borrar código. Compare el avance existente y registre:

```markdown
# ESTADO_RAMA — <rama> — <fecha>
| Requisito/criterio | Archivo o evidencia | Estado | Acción/owner |
|---|---|---|---|
| <ID> | <ruta, validación y resultado> | CONFORME/PARCIAL/DIVERGE/NO_VERIFICADO | <acción> |
Gates: privacidad=<estado>; elegibilidad-sin-LLM=<estado>; contratos=<estado>; snapshot=<estado>
Decisiones/adaptadores pendientes: <DEC-ID o ninguno>
```

- `CONFORME`: evidencia ejecutada satisface el criterio.
- `PARCIAL`: solo parte del criterio está cubierta.
- `DIVERGE`: contradice requisito o contrato; deténgase y abra `DEC-*`.
- `NO_VERIFICADO`: no hay evidencia suficiente.

Conserve código conforme. Para divergencias, acuerde adaptar código o cambiar primero la autoridad documental. Un adaptador temporal vive en el borde, tiene prueba y fecha de retiro.

## 5. Integración y gates

Orden: privacidad/fixtures → C0–C4 → motor/datos → API/auth/snapshot → frontend contra mocks → contenido validado → E2E/IaC. Antes de integrar:

- **Privacidad:** solo sintéticos rotulados; allowlist antes de servicios downstream; logs sin cuerpos.
- **Determinismo:** elegibilidad, acceso y U/B/V fuera del LLM; parámetros no hardcodeados.
- **Contratos:** C0–C4, ejemplos y OpenAPI compatibles/versionados.
- **Snapshot:** `CONTROL/ACTIVE` es única autoridad y sus seis campos se actualizan juntos.
- **AWS:** estado cambia solo con smoke test fechado/sanitizado; fallback seguro disponible.

Si algo contradice la [fuente inmutable](./especificacion/PROYECTO_3_ESPECIFICACION_v2.md), deténgase. Registre la decisión en [`DECISIONES_SUPUESTOS_PREGUNTAS.md`](../.kiro/specs/_shared/DECISIONES_SUPUESTOS_PREGUNTAS.md), corrija maestro/contrato y luego consumidores.

## 6. Prompts seguros copiables

**Auditoría sin modificar (Vibe):**

```text
Lee #File .kiro/specs/INDICE.md, el spec de mi rol y C0-C4. Revisa solo mi rama. Crea la matriz criterio → evidencia → CONFORME/PARCIAL/DIVERGE/NO_VERIFICADO. No edites, no marques tareas sin ejecutar su validación y no muestres valores personales.
```

**Gap pequeño (Vibe):**

```text
Para <ID>, compara #File <spec> con #File <archivo>. Propón el cambio mínimo que conserve el avance. Si diverge un contrato o cambia conducta visible, detente y redacta una decisión; no cambies la Spec silenciosamente.
```

**Adopción (Spec + Supervised):**

```text
Usa las Specs aprobadas como baseline y #File ESTADO_RAMA.md. Conserva CONFORME, divide PARCIAL, bloquea DIVERGE en DEC-* y deja NO_VERIFICADO sin marcar. Incluye owner, dependencia, validación y evidencia por tarea.
```

Nunca pegue credenciales, tokens, account IDs, endpoints privados, cuerpos de prompts ni datos reales. Para AWS use payloads completamente sintéticos y registre solo fecha, región, operación y resultado sanitizado.
