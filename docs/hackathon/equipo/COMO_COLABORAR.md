# Cómo colaborar desde Kiro

Trabajamos por componente y tarea, no “cada quien en su carpeta”. El ownership, los handoffs y los horarios de integración están en [Roles y responsabilidades](ROLES_Y_RESPONSABILIDADES.md).

Antes de cambiar algo, consulte:

- [Especificación](../../especificacion/PROYECTO_3_ESPECIFICACION_v2.md)
- [Estructura del repositorio](ESTRUCTURA_REPOSITORIO_INICIAL.md)
- [Flujo de la ficha](../../producto/FLUJO_DE_FICHA.md)
- [README principal](../../../README.md)

## Flujo simple

```text
Pull → rama de tarea → cambio coordinado → validar → commit → push
```

Todo puede hacerse desde **Source Control** de Kiro (`Ctrl+Shift+G`).

1. **Pull:** traiga los cambios antes de empezar.
2. **Rama:** cree una rama breve por tarea, por ejemplo `datos/loader` o `front/ficha-familia`. No trabaje directamente en `main`.
3. **Coordinar:** avise al dueño del componente. Si tocará `README.md`, contratos, esquemas o documentos compartidos, acuerde el cambio antes.
4. **Cambiar:** edite solo el componente de la tarea. No duplique lógica de elegibilidad o prioridad en frontend ni use Bedrock para decidir resultados.
5. **Validar:** revise los archivos modificados y ejecute las comprobaciones existentes del componente una sola vez.
6. **Commit:** prepare únicamente los archivos de la tarea y use un mensaje corto, por ejemplo `docs: aclara contrato de datos`.
7. **Push:** suba la rama para revisión. El dueño del componente aprueba antes de integrar.

## Trabajo en paralelo

- Frontend usa los mocks publicados por Computación hasta disponer del API real.
- Computación usa un conjunto pequeño del contrato de datos hasta recibir la carga completa de Mecánica.
- Recursos Naturales entrega criterios, lenguaje y hallazgos manuales sin necesidad de programar.
- Un bloqueo de más de 30 minutos se informa con qué falta, quién depende y qué mock permitiría seguir.
- Hay integración a las 10:00, 14:00 y demo interna a las 19:00.

## Conflictos

Si Kiro marca un conflicto, no elija una versión a ciegas. Compare ambos cambios y consulte a las personas dueñas de los componentes involucrados. Resuelva, vuelva a validar y recién entonces haga commit.

## Reglas de seguridad y alcance

- Nunca suba `.env`, claves, credenciales, datos reales, bases locales o dumps.
- Los 23 CSV de `data/publico/` son canónicos; no los edite sin una decisión explícita del equipo.
- `dataset_e3.json` no sustituye los CSV porque omite `condiciones_integrante.csv`.
- No cree carpetas personales, código ficticio, dependencias o scaffolding sin acuerdo técnico.
- Bedrock solo redacta con contexto filtrado; el motor determinista decide.
- Revise que toda salida diga que es orientación referencial y debe confirmarse en la institución.

Si algo falla, no fuerce Git ni oculte el problema: comparta el estado y pida revisión.
