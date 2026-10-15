// Selección con controles nativos dentro de fieldset/legend (design.md §10.3): única (radios con
// forma de chip) o múltiple (checkboxes visibles).
import { useId } from 'react';
import { Icon } from './icons';

export interface ChoiceOption {
  readonly value: string;
  readonly label: string;
}

export interface ChoiceChipsProps {
  readonly legend: string;
  readonly options: readonly ChoiceOption[];
  readonly value: string | null;
  readonly onChange: (value: string) => void;
}

export function ChoiceChips({ legend, options, value, onChange }: ChoiceChipsProps) {
  const name = useId();
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 font-semibold">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const checked = option.value === value;
          return (
            <label
              key={option.value}
              className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full border-2 border-border-strong bg-surface px-4 font-semibold has-[:checked]:border-primary has-[:checked]:bg-primary has-[:checked]:text-surface has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus"
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={checked}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              {checked && <Icon name="check" className="size-5" />}
              <span>{option.label}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export interface CheckListProps {
  readonly legend: string;
  readonly options: readonly ChoiceOption[];
  readonly values: ReadonlySet<string>;
  readonly onToggle: (value: string) => void;
}

/** Selección múltiple con checkboxes nativos visibles (lista vertical, una opción por fila). */
export function CheckList({ legend, options, values, onToggle }: CheckListProps) {
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 font-semibold">{legend}</legend>
      <div className="flex flex-col gap-2">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border-2 border-border-strong bg-surface px-4 py-2 font-semibold has-[:checked]:border-primary has-[:checked]:bg-canvas has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus"
          >
            <input
              type="checkbox"
              value={option.value}
              checked={values.has(option.value)}
              onChange={() => onToggle(option.value)}
              className="size-6 shrink-0 accent-primary"
            />
            <span className="c3-text">{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
