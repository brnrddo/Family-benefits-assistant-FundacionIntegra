// Rutas (design.md §9). Las páginas se cargan diferidas; la raíz captura cualquier error de render
// o de carga de chunk con RouteErrorPage (sin mensaje, stack ni status). `/familias/:id/agregar-informacion`
// responde "No encontrada" en `escala` (la página consulta `capabilities.addInfo`, DEC-039). "Familia
// nueva" salió de la demo (plan de arreglos): `/familia-nueva` cae en "No encontrada".
import { lazy } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import AppShell from './features/system/AppShell';
import RouteErrorPage from './features/system/RouteErrorPage';

const HomePage = lazy(() => import('./features/home/HomePage'));
const FamilyPage = lazy(() => import('./features/family/FamilyPage'));
const ScriptPage = lazy(() => import('./features/script/ScriptPage'));
const MessagePage = lazy(() => import('./features/message/MessagePage'));
const ConversationPage = lazy(() => import('./features/conversation/ConversationPage'));
const AddInfoPage = lazy(() => import('./features/add-info/AddInfoPage'));
const KpiPage = lazy(() => import('./features/kpi/KpiPage'));
const AssistantPage = lazy(() => import('./features/assistant/AssistantPage'));
const NotFoundPage = lazy(() => import('./features/system/NotFoundPage'));

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'familias/:familyId', element: <FamilyPage /> },
      { path: 'familias/:familyId/guion', element: <ScriptPage /> },
      { path: 'familias/:familyId/mensaje', element: <MessagePage /> },
      { path: 'familias/:familyId/conversacion', element: <ConversationPage /> },
      // DEC-039: operación propuesta; responde "No encontrada" sin `capabilities.addInfo` (escala).
      { path: 'familias/:familyId/agregar-informacion', element: <AddInfoPage /> },
      { path: 'avance', element: <KpiPage /> },
      { path: 'preguntar', element: <AssistantPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(routes);
}
