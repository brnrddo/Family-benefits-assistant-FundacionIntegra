// Jardín seleccionado compartido vía `?jardin=` (design.md §9). Un ID inválido o no autorizado
// cae al primero de la lista de C3 y la URL se reescribe con replace. Con sesión demo activa el jardín
// es fijo (el de la sesión): `gardens` trae solo ese y `select` no hace nada, así no hay selector.
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import type { JardinSummary } from '../../api/types';
import { useJardines } from '../../data/queries';
import { useDemoSession } from '../demo-session/session';

export function useSelectedGarden() {
  const jardines = useJardines();
  const demo = useDemoSession();
  const [search, setSearch] = useSearchParams();
  const fixedId = demo.active && demo.seed !== null ? demo.seed.garden.garden_id : null;
  const requested = fixedId ?? search.get('jardin');
  const all: readonly JardinSummary[] = jardines.data?.body.items ?? [];
  const garden = all.find((g) => g.garden_id === requested) ?? all[0];
  const gardens: readonly JardinSummary[] = fixedId !== null ? (garden !== undefined ? [garden] : []) : all;
  const urlGarden = search.get('jardin');
  useEffect(() => {
    if (fixedId !== null) return;
    if (urlGarden !== null && garden !== undefined && garden.garden_id !== urlGarden) {
      setSearch(
        (params) => {
          params.set('jardin', garden.garden_id);
          return params;
        },
        { replace: true },
      );
    }
  }, [fixedId, urlGarden, garden, setSearch]);
  const select = useCallback(
    (gardenId: string) => {
      if (fixedId !== null) return;
      setSearch(
        (params) => {
          params.set('jardin', gardenId);
          return params;
        },
        { replace: true },
      );
    },
    [fixedId, setSearch],
  );
  return { jardines, gardens, garden, select };
}
