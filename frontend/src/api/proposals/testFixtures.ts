// SOLO PRUEBAS (mismo criterio que src/test/fixtures.ts): fixtures sintéticos de la propuesta
// "Agregar información" para pruebas de vistas, que no pueden importar src/mocks/** (FE-003).
// Ningún módulo de la app lo importa.
import engineCodes from '../../mocks/proposals/addFamiliaAntecedentes.engineCodes.json';
import antecedentes from '../../mocks/proposals/getFamiliaAntecedentes.FAM-SIM-E3-00002.json';

/** Ficha con códigos del motor y GET /antecedentes con `pregnancy_weeks_threshold` (SYNTHETIC_DEMO_NOT_A_REAL_PERSON). */
export const addInfoEngineCodes = engineCodes;

/** Respuesta del handler MSW de GET /familias/{id}/antecedentes (SYNTHETIC_DEMO_NOT_A_REAL_PERSON). */
export const getAntecedentesFixture = antecedentes;
