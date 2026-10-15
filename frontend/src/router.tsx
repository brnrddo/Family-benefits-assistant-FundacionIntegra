// Rutas (design.md §9). Las páginas se cargan diferidas; la raíz captura cualquier error de render
// o de carga de chunk con RouteErrorPage (sin mensaje, stack ni status). `/familia-nueva` responde
// "No encontrada" en `escala` (la página consulta `capabilities.newFamily` al renderizar, SUP-038).
import { lazy } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import AppShell from './features/system/AppShell';
import RouteErrorPage from './features/system/RouteErrorPage';

const HomePage = lazy(() => import('./features/home/HomePage'));
const FamilyPage = lazy(() => import('./features/family/FamilyPage'));
const ScriptPage = lazy(() => import('./features/script/ScriptPage'));
const MessagePage = lazy(() => import('./features/message/MessagePage'));
const ConversationPage = lazy(() => import('./features/conversation/ConversationPage'));
const NewFamilyPage = lazy(() => import('./features/new-family/NewFamilyPage'));
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
      { path: 'familia-nueva', element: <NewFamilyPage /> },
      { path: 'avance', element: <KpiPage /> },
      { path: 'preguntar', element: <AssistantPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(routes);
}
