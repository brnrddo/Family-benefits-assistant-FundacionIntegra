// Editor del "nombre de trato" (DEC-038): la tía escribe el nombre del niño o niña y queda SOLO en
// este equipo (offline/localNames.ts). No se envía a la API ni va a logs. Solo se renderiza con
// `capabilities.localNames` (local/demo sintético); en `escala` no existe (DEC-038).
import { useId, useState, type FormEvent } from 'react';
import { formatInteger } from '../../domain/format';
import { t } from '../../i18n/copy';
import {
  LOCAL_NAME_MAX_LENGTH,
  removeLocalName,
  saveLocalName,
  useLocalNames,
  type LocalNameIssue,
} from '../../offline/localNames';
import { Button } from '../../ui/Button';
import { Icon } from '../../ui/icons';

type Issue = LocalNameIssue | 'unavailable';

function issueText(issue: Issue): string {
  switch (issue) {
    case 'empty':
      return t('family.name.error_empty');
    case 'too_long':
      return t('family.name.error_too_long', { max: formatInteger(LOCAL_NAME_MAX_LENGTH) });
    case 'invalid_chars':
      return t('family.name.error_chars');
    case 'unavailable':
      return t('family.name.save_failed');
  }
}

export function NameEditor({ familyId }: { readonly familyId: string }) {
  const names = useLocalNames();
  const current = names.get(familyId);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [issue, setIssue] = useState<Issue | null>(null);
  const [status, setStatus] = useState<'saved' | 'removed' | null>(null);
  const [busy, setBusy] = useState(false);
  const regionId = useId();
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();

  const toggle = () => {
    setDraft(current ?? '');
    setIssue(null);
    setStatus(null);
    setOpen((value) => !value);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    const result = await saveLocalName(familyId, draft);
    setBusy(false);
    if (!result.ok) {
      setIssue(result.issue);
      return;
    }
    // DEC-047: el texto crudo (con apellido) no queda en memoria tras guardar.
    setDraft('');
    setIssue(null);
    setStatus('saved');
    setOpen(false);
  };

  const remove = async () => {
    setBusy(true);
    await removeLocalName(familyId).catch(() => undefined);
    setBusy(false);
    setIssue(null);
    setStatus('removed');
    setOpen(false);
  };

  return (
    <div data-name-editor className="space-y-2">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={regionId}
        onClick={toggle}
        className="inline-flex min-h-12 items-center gap-2 rounded-xl px-1 font-semibold text-primary"
      >
        <Icon name="pencil" className="size-5" />
        {current === undefined ? t('family.name.open') : t('family.name.change')}
      </button>
      <div id={regionId} hidden={!open}>
        {open && (
          <form onSubmit={(event) => void submit(event)} className="space-y-3 rounded-card border border-border bg-surface p-4">
            <label htmlFor={inputId} className="block font-semibold">
              {t('family.name.title')}
            </label>
            <p id={hintId} className="text-ink-muted">
              {t('family.name.hint')} {t('family.name.demo_hint')}
            </p>
            <input
              id={inputId}
              type="text"
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                setIssue(null);
              }}
              maxLength={LOCAL_NAME_MAX_LENGTH}
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              aria-invalid={issue !== null || undefined}
              aria-describedby={issue !== null ? `${hintId} ${errorId}` : hintId}
              className="min-h-12 w-full rounded-xl border-2 border-border-strong bg-surface px-3 font-semibold"
            />
            {issue !== null && (
              <p id={errorId} role="alert" className="font-semibold text-danger-ink">
                {issueText(issue)}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" icon="check" busy={busy}>
                {t('family.name.save')}
              </Button>
              {current !== undefined && (
                <Button variant="secondary" disabled={busy} onClick={() => void remove()}>
                  {t('family.name.remove')}
                </Button>
              )}
            </div>
          </form>
        )}
      </div>
      <p role="status" className="text-ink-muted">
        {status === 'saved' ? t('family.name.saved') : status === 'removed' ? t('family.name.removed') : ''}
      </p>
    </div>
  );
}
