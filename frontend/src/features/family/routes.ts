// Rutas internas de una familia: se arman con generatePath desde IDs ya validados (NIT 11).
import { generatePath } from 'react-router';

export const familyRoutes = {
  ficha: (familyId: string) => generatePath('/familias/:familyId', { familyId }),
  guion: (familyId: string) => generatePath('/familias/:familyId/guion', { familyId }),
  mensaje: (familyId: string) => generatePath('/familias/:familyId/mensaje', { familyId }),
  conversacion: (familyId: string) => generatePath('/familias/:familyId/conversacion', { familyId }),
};
