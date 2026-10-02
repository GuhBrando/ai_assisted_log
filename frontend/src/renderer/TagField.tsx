import React, { useEffect, useMemo, useRef, useState } from 'react';

export function TagField({
  value,
  onChange,
  suggestions,
}: {
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
}): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const selected = value
    .split(',')
    .slice(0, -1)
    .map((tag) => tag.trim().toLowerCase());
  const needle = value.split(',').at(-1)?.trim().toLowerCase() ?? '';
  const options = useMemo(
    () =>
      suggestions
        .filter((tag) => !selected.includes(tag) && tag.includes(needle))
        .slice(0, 8),
    [suggestions, needle, selected.join('|')],
  );

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent): void => {
      if (root.current && !root.current.contains(event.target as Node))
        setOpen(false);
    };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, [open]);

  function choose(tag: string): void {
    const before = value
      .split(',')
      .slice(0, -1)
      .map((item) => item.trim())
      .filter(Boolean);
    onChange([...before, tag].join(', '));
    setOpen(false);
    setActive(0);
    input.current?.focus();
  }
  function keyDown(event: React.KeyboardEvent<HTMLInputElement>): void {
    if (event.key === 'Escape') {
      setOpen(false);
      return;
    }
    if (event.key === 'ArrowDown' && options.length) {
      event.preventDefault();
      setOpen(true);
      setActive((index) => (index + 1) % options.length);
    }
    if (event.key === 'ArrowUp' && options.length) {
      event.preventDefault();
      setOpen(true);
      setActive((index) => (index - 1 + options.length) % options.length);
    }
    if (event.key === 'Enter' && open && options.length) {
      event.preventDefault();
      choose(options[active] ?? options[0]);
    }
  }
  return (
    <div className="tag-field wide-field" ref={root}>
      <div className="field-head">
        <label htmlFor="tag-filter">Tags</label>
        <span className="field-hint">separadas por vírgula</span>
      </div>
      <div className="tag-control">
        <input
          ref={input}
          id="tag-filter"
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={keyDown}
          placeholder="team:payments, feature:pix"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open && options.length > 0}
          aria-controls="tag-suggestions"
        />
        {value && (
          <button
            type="button"
            className="date-icon"
            onClick={() => {
              onChange('');
              setOpen(false);
              input.current?.focus();
            }}
            aria-label="Limpar tags"
          >
            ×
          </button>
        )}
      </div>
      <span className="field-feedback">
        Sugestões disponíveis apenas desta página
      </span>
      {open && options.length > 0 && (
        <div
          className="tag-popover"
          id="tag-suggestions"
          role="listbox"
          aria-label="Sugestões de tags desta página"
        >
          {options.map((tag, index) => (
            <button
              type="button"
              role="option"
              aria-selected={index === active}
              className={index === active ? 'active' : ''}
              key={tag}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
