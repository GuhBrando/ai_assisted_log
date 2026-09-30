import React, { useEffect, useRef, useState } from 'react';
import { formatDateTime, parseDateTime } from './log-utils';

type TimePart = 'hour' | 'minute' | 'second';
type TimeParts = Record<TimePart, string>;
const weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
const pad = (value: number): string => String(value).padStart(2, '0');

function partsFor(date: Date | null): TimeParts {
  return {
    hour: pad(date?.getHours() ?? 0),
    minute: pad(date?.getMinutes() ?? 0),
    second: pad(date?.getSeconds() ?? 0),
  };
}

function calendarDays(month: Date): Array<Date | null> {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const offset = (first.getDay() + 6) % 7;
  return Array.from({ length: 42 }, (_, index) => {
    const day = index - offset + 1;
    return day > 0 &&
      day <= new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
      ? new Date(month.getFullYear(), month.getMonth(), day)
      : null;
  });
}

export function DateTimeField({
  id,
  label,
  hint,
  value,
  onChange,
  minValue,
  error,
}: {
  id: string;
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  minValue?: string;
  error?: string;
}): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [viewMonth, setViewMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selected, setSelected] = useState<Date | null>(null);
  const [time, setTime] = useState<TimeParts>({
    hour: '00',
    minute: '00',
    second: '00',
  });
  const [pickerError, setPickerError] = useState('');
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const min = minValue ? parseDateTime(minValue) : null;

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent): void => {
      if (root.current && !root.current.contains(event.target as Node))
        setOpen(false);
    };
    const closeEscape = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', closeEscape);
    };
  }, [open]);

  function openPicker(): void {
    const parsed = parseDateTime(value);
    const anchor = parsed ?? new Date();
    setSelected(parsed);
    setTime(partsFor(parsed));
    setViewMonth(new Date(anchor.getFullYear(), anchor.getMonth(), 1));
    setPickerError('');
    setOpen((current) => !current);
  }
  function commit(day: Date, parts: TimeParts): void {
    const numbers = [parts.hour, parts.minute, parts.second].map(Number);
    if (
      Object.values(parts).some(
        (value) => value === '' || !/^\d{1,2}$/.test(value),
      ) ||
      numbers[0] > 23 ||
      numbers[1] > 59 ||
      numbers[2] > 59
    ) {
      setPickerError('Horário inválido.');
      return;
    }
    const next = new Date(
      day.getFullYear(),
      day.getMonth(),
      day.getDate(),
      numbers[0],
      numbers[1],
      numbers[2],
    );
    if (min && next.getTime() <= min.getTime()) {
      setPickerError('O fim deve ser posterior ao início.');
      return;
    }
    setPickerError('');
    onChange(formatDateTime(next));
  }
  function chooseDay(day: Date): void {
    const adjusted = { ...time };
    if (min && day.toDateString() === min.toDateString()) {
      const candidate = new Date(
        day.getFullYear(),
        day.getMonth(),
        day.getDate(),
        Number(time.hour),
        Number(time.minute),
        Number(time.second),
      );
      if (candidate <= min) {
        const following = new Date(min.getTime() + 1000);
        if (following.getDate() !== day.getDate()) return;
        Object.assign(adjusted, partsFor(following));
        setTime(adjusted);
      }
    }
    setSelected(day);
    commit(day, adjusted);
  }
  function updateTime(part: TimePart, raw: string): void {
    if (raw.length > 2) return;
    const next = { ...time, [part]: raw };
    setTime(next);
    if (selected) commit(selected, next);
  }
  function edit(value: string): void {
    onChange(value);
    const parsed = parseDateTime(value);
    if (parsed) {
      setSelected(parsed);
      setTime(partsFor(parsed));
      setViewMonth(new Date(parsed.getFullYear(), parsed.getMonth(), 1));
    }
  }
  const selectedDate = parseDateTime(value);
  return (
    <div className="date-field" ref={root}>
      <div className="field-head">
        <label htmlFor={id}>{label}</label>
        <span className="field-hint">{hint}</span>
      </div>
      <div className={`date-control ${error ? 'invalid' : ''}`}>
        <input
          id={id}
          className="date-text mono"
          type="text"
          inputMode="numeric"
          placeholder="DD/MM/AAAA HH:MM:SS"
          value={value}
          onChange={(event) => edit(event.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={`${id}-feedback`}
          maxLength={19}
        />
        {value && (
          <button
            type="button"
            className="date-icon"
            onClick={() => {
              onChange('');
              setSelected(null);
              setPickerError('');
            }}
            aria-label={`Limpar ${label.toLowerCase()}`}
          >
            ×
          </button>
        )}
        <button
          type="button"
          ref={trigger}
          className="date-icon calendar-trigger"
          onClick={openPicker}
          aria-label={`Abrir calendário de ${label.toLowerCase()}`}
          aria-expanded={open}
          aria-controls={`${id}-calendar`}
        >
          ▦
        </button>
      </div>
      <span
        id={`${id}-feedback`}
        className="field-feedback"
        role={error ? 'alert' : undefined}
      >
        {error ?? '\u00a0'}
      </span>
      {open && (
        <div
          className="date-popover"
          id={`${id}-calendar`}
          role="dialog"
          aria-label={`Calendário de ${label.toLowerCase()}`}
        >
          <div className="calendar-heading">
            <button
              type="button"
              onClick={() =>
                setViewMonth(
                  new Date(
                    viewMonth.getFullYear(),
                    viewMonth.getMonth() - 1,
                    1,
                  ),
                )
              }
              aria-label="Mês anterior"
            >
              ‹
            </button>
            <strong>
              {new Intl.DateTimeFormat('pt-BR', {
                month: 'long',
                year: 'numeric',
              }).format(viewMonth)}
            </strong>
            <button
              type="button"
              onClick={() =>
                setViewMonth(
                  new Date(
                    viewMonth.getFullYear(),
                    viewMonth.getMonth() + 1,
                    1,
                  ),
                )
              }
              aria-label="Próximo mês"
            >
              ›
            </button>
          </div>
          <div className="calendar-grid">
            {weekdays.map((day) => (
              <span className="calendar-weekday" key={day}>
                {day}
              </span>
            ))}
            {calendarDays(viewMonth).map((day, index) =>
              day ? (
                <button
                  type="button"
                  key={index}
                  className={
                    selectedDate?.toDateString() === day.toDateString()
                      ? 'chosen'
                      : ''
                  }
                  disabled={Boolean(
                    min &&
                    new Date(
                      day.getFullYear(),
                      day.getMonth(),
                      day.getDate() + 1,
                    ) <= min,
                  )}
                  onClick={() => chooseDay(day)}
                  aria-label={new Intl.DateTimeFormat('pt-BR', {
                    dateStyle: 'full',
                  }).format(day)}
                  aria-pressed={
                    selectedDate?.toDateString() === day.toDateString()
                  }
                >
                  {day.getDate()}
                </button>
              ) : (
                <span key={index} />
              ),
            )}
          </div>
          <div className="calendar-time">
            <span>Horário</span>
            {(['hour', 'minute', 'second'] as const).map((part) => (
              <label key={part}>
                <span>
                  {part === 'hour' ? 'Hora' : part === 'minute' ? 'Min' : 'Seg'}
                </span>
                <input
                  type="number"
                  min="0"
                  max={part === 'hour' ? '23' : '59'}
                  value={time[part]}
                  onChange={(event) => updateTime(part, event.target.value)}
                  aria-label={
                    part === 'hour'
                      ? 'Hora'
                      : part === 'minute'
                        ? 'Minuto'
                        : 'Segundo'
                  }
                />
              </label>
            ))}
          </div>
          {pickerError && (
            <p className="calendar-error" role="alert">
              {pickerError}
            </p>
          )}
          <div className="calendar-footer">
            <span>
              {selectedDate ? formatDateTime(selectedDate) : 'Selecione um dia'}
            </span>
            <button
              type="button"
              className="quiet-button"
              onClick={() => setOpen(false)}
            >
              Concluir
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
