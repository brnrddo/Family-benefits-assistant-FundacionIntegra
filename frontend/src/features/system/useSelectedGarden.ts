// Jardín seleccionado compartido vía `?jardin=` (design.md §9). Un ID inválido o no autorizado
// cae al primero de la lista de C3 y la URL se reescribe con replace.
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import type { JardinSummary } from '../../api/types';
import { useJardines } from '../../data/queries';

export function useSelectedGarden() {
  const jardines = useJardines();
  const [search, setSearch] = useSearchParams();
  const requested = search.get('jardin');
  const gardens: readonly JardinSummary[] = jardines.data?.body.items ?? [];
  const garden = gardens.find((g) => g.garden_id === requested) ?? gardens[0];

  useEffect(() => {
    if (requested !== null && garden !== undefined && garden.garden_id !== requested) {
      setSearch(
        (params) => {
          params.set('jardin', garden.garden_id);
          return params;
        },
        { replace: true },
      );
    }
  }, [requested, garden, setSearch]);

  const select = useCallback(
    (gardenId: string) =>
      setSearch(
        (params) => {
          params.set('jardin', gardenId);
          return params;
        },
        { replace: true },
      ),
    [setSearch],
  );

  return { jardines, gardens, garden, select };
}
