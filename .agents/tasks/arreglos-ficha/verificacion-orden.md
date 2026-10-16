# Verificación · Orden de beneficios en la ficha + "Qué hacer ahora" + bug C

Fecha: 2026-10-15. Rama `arreglos-ficha-orden` (base `c9cd006`). Solo frontend; backend sin cambios (no se corrió pytest).

## Test rojo primero

`npx vitest --run src/domain/benefitGroups.test.ts src/features/family/actionPlan.test.ts` (cwd `frontend`), antes de implementar:

```
FAIL  src/domain/benefitGroups.test.ts > benefitSections > reparte por estado, respeta el orden de la lista prioridad y omite NO_APLICA
TypeError: benefitSections is not a function
Test Files  2 failed (2)
Tests  1 failed (1)
```

(`actionPlan.test.ts` falló al importar `./actionPlan`, todavía inexistente.)

## Verificación intermedia

`npx tsc -p tsconfig.app.json --noEmit; npx vitest --run src/features/family src/domain src/features/add-info`:

```
Test Files  1 failed | 9 passed (10)
Tests  1 failed | 35 passed (36)
```

El fallo estaba en el propio test de bug C (`waitFor` devolvía `null` en vez de esperar la sección). Se cambió a `findByRole('heading', { name: FAMILY_COPY.sectionMissing })`.

## Verificación final (una vez)

`npm run check` (cwd `frontend`), exit 0:

```
> npm run typecheck && npm run lint && npm run test && npm run build && npm run check:budget
typecheck: tsc -p tsconfig.app.json --noEmit && tsc -p tsconfig.node.json --noEmit   (sin errores)
lint: eslint . --max-warnings=0                                                      (sin salida)
test: Test Files  45 passed (45) · Tests  407 passed (407)
build: ✓ built in 1.20s
check:budget OK
```

## Render

- Lo cubren los tests de render de `FamilyPage.test.tsx`: secciones en el orden de C3, filtro (radios nativos de `ChoiceChips`) con conteos, "Ya postuló o sin cupo" plegada (`aria-expanded=false`), tarjeta cerrada sin chips visibles y abierta con "Falta saber" + la pregunta de C3, filtro que deja una sola sección y "Qué hacer ahora" con la pregunta y "Entréguele la información de: …". El test de bug C cubre la tarjeta, "Datos por confirmar" (tarjeta del hogar abierta con su botón) y el plan con el texto del documento, sin "Un dato del hogar".
- **No verificado:** captura a 360 px. Esta sesión no puede levantar `vite` (la herramienta bloquea comandos de servidor), así que no hubo Playwright ni navegador. El filtro usa el `ChoiceChips` existente (`flex flex-wrap gap-2`), igual que el selector "Ordenar por" anterior. Hay que revisarlo a 360 px en el ensayo de demo.
- **No verificado:** bug C contra el backend real (`E3_MOCK=0`), por la misma razón. El test reproduce la forma exacta que entrega el backend según el diagnóstico (`SI/PRELIMINAR/PENDIENTE_ANTECEDENTES`, `missing_codes: []`). Verificar en el ensayo de demo.

## Fuera de lista permitida / pendiente

- `frontend/src/features/add-info/AddInfoPage.test.tsx`: se ajustaron solo las 6 líneas que abrían "Ver todos los beneficios" (ese botón ya no existe), sin tocar los hunks de la rama `arreglos-ficha-t7` (import de la línea 9 y test nuevo cerca de la línea 98). El merge debería ser limpio.
- `frontend/e2e/smoke.spec.ts` (de B) todavía espera `family.top_title`, `family.applies_title` y `[data-benefit-group="missing"] h3`. No se tocó ni se corrió. B tiene que actualizarlo a `FAMILY_COPY.section*` y `[data-benefit-section="missing"] h3`.
