// @vitest-environment jsdom
import React, { useState } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DateTimeField } from './DateTimeField';
import { TagField } from './TagField';

afterEach(cleanup);

function DateHarness({
  initial = '',
  minValue,
}: {
  initial?: string;
  minValue?: string;
}): React.JSX.Element {
  const [value, setValue] = useState(initial);
  return (
    <DateTimeField
      id="test-date"
      label="Fim"
      hint="exclusivo"
      value={value}
      onChange={setValue}
      minValue={minValue}
    />
  );
}

function TagHarness(): React.JSX.Element {
  const [value, setValue] = useState('');
  return (
    <TagField
      value={value}
      onChange={setValue}
      suggestions={['feature:pix', 'team:payments', 'team:platform']}
    />
  );
}

describe('controles de filtro', () => {
  it('abre, troca data e horário, fecha por Escape e limpa o valor sem mudar o formato', async () => {
    const user = userEvent.setup();
    render(<DateHarness initial="14/09/2026 10:00:00" />);
    await user.click(
      screen.getByRole('button', { name: 'Abrir calendário de fim' }),
    );
    expect(
      screen.getByRole('dialog', { name: 'Calendário de fim' }),
    ).toBeTruthy();
    await user.click(
      screen.getByRole('button', { name: /15 de setembro de 2026/i }),
    );
    expect(
      (screen.getByRole('textbox', { name: 'Fim' }) as HTMLInputElement).value,
    ).toBe('15/09/2026 10:00:00');
    const hour = screen.getByRole('spinbutton', { name: 'Hora' });
    await user.clear(hour);
    await user.type(hour, '12');
    expect(
      (screen.getByRole('textbox', { name: 'Fim' }) as HTMLInputElement).value,
    ).toBe('15/09/2026 12:00:00');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Limpar fim' }));
    expect(
      (screen.getByRole('textbox', { name: 'Fim' }) as HTMLInputElement).value,
    ).toBe('');
  });
  it('não permite escolher fim anterior ao início pelo calendário', async () => {
    const user = userEvent.setup();
    render(
      <DateHarness
        initial="15/09/2026 11:00:00"
        minValue="14/09/2026 10:00:00"
      />,
    );
    await user.click(
      screen.getByRole('button', { name: 'Abrir calendário de fim' }),
    );
    expect(
      (
        screen.getByRole('button', {
          name: /13 de setembro de 2026/i,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await user.click(
      screen.getByRole('button', { name: /14 de setembro de 2026/i }),
    );
    expect(
      (screen.getByRole('textbox', { name: 'Fim' }) as HTMLInputElement).value,
    ).toBe('14/09/2026 11:00:00');
  });
  it('sugere só tags recebidas, aceita teclado e limpeza individual', async () => {
    const user = userEvent.setup();
    render(<TagHarness />);
    const field = screen.getByRole('combobox', { name: 'Tags' });
    await user.type(field, 'team:pa');
    expect(screen.getByRole('option', { name: 'team:payments' })).toBeTruthy();
    await user.keyboard('{Enter}');
    expect((field as HTMLInputElement).value).toBe('team:payments');
    await user.click(screen.getByRole('button', { name: 'Limpar tags' }));
    expect((field as HTMLInputElement).value).toBe('');
  });
});
