// @vitest-environment jsdom
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { LogQuery } from '../contracts';
import type { LogApi, LogRead } from '../contracts';
import { Logs } from './Logs';

const sample: LogRead = {
  id: '66f96a0de4b0a1b2c3d4e5f7',
  application_id: '66f8b112e4b0a1b2c3d4e5f9',
  application_name: 'Checkout',
  correlation_id: 'b09bd080-04e0-4aa0-9c66-9112f0f46664',
  level: 4,
  message: 'Falha ao cobrar',
  exception: 'ValueError: pagamento recusado\n  at cobrar()',
  environment: 'prod',
  information_data: { attempt: 2 },
  tags: ['team:payments'],
  occurred_at: '2026-09-29T14:03:12.481Z',
  received_at: '2026-09-29T14:03:13.000Z',
  expire_at: '2026-10-29T14:03:13.000Z',
};

const apiTarget = async () => ({
  ok: true as const,
  data: { url: 'http://127.0.0.1:8000', mock: false },
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('investigação visual', () => {
  it('mostra dados resumidos e busca o detalhe completo com stack trace', async () => {
    const getLog = vi.fn(async () => ({ ok: true as const, data: sample }));
    const api = {
      apiTarget,
      listApplications: async () => ({
        ok: true as const,
        data: { items: [] },
      }),
      listLogs: async () => ({
        ok: true as const,
        data: { items: [sample], next_cursor: null },
      }),
      getLog,
    } as unknown as LogApi;
    vi.stubGlobal('logApi', api);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <Logs onLogout={() => {}} onExpired={() => {}} />
      </QueryClientProvider>,
    );
    const row = await screen.findByRole('button', { name: /Falha ao cobrar/ });
    expect(row.textContent).toContain('ERROR');
    expect(screen.getByText('Busca somente na página carregada')).toBeTruthy();
    expect(await screen.findByText('API local · 127.0.0.1:8000')).toBeTruthy();
    await userEvent.click(row);
    await waitFor(() => expect(getLog).toHaveBeenCalledWith(sample.id));
    expect(
      await screen.findByText(/ValueError: pagamento recusado/),
    ).toBeTruthy();
    expect(screen.getByText(sample.correlation_id!)).toBeTruthy();
  });
});

function mountList(
  listLogs: (query: LogQuery) => Promise<{
    ok: true;
    data: { items: LogRead[]; next_cursor: string | null };
  }>,
): void {
  const api = {
    apiTarget,
    listApplications: async () => ({ ok: true as const, data: { items: [] } }),
    listLogs,
    getLog: async () => ({ ok: true as const, data: sample }),
  } as unknown as LogApi;
  vi.stubGlobal('logApi', api);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <Logs onLogout={() => {}} onExpired={() => {}} />
    </QueryClientProvider>,
  );
}

describe('paginação e filtros na tela', () => {
  it('habilita ambos na página intermediária e recusa período invertido', async () => {
    const list = vi.fn(async (query: LogQuery) => ({
      ok: true as const,
      data: {
        items: [
          {
            ...sample,
            id:
              query.cursor === 'terceira'
                ? '66f96a0de4b0a1b2c3d4e5f1'
                : query.cursor === 'segunda'
                  ? '66f96a0de4b0a1b2c3d4e5f2'
                  : sample.id,
          },
        ],
        next_cursor:
          query.cursor === 'segunda'
            ? 'terceira'
            : query.cursor
              ? null
              : 'segunda',
      },
    }));
    mountList(list);
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Próxima' }));
    await waitFor(() => expect(screen.getByText(/Página 2/)).toBeTruthy());
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
    expect(
      (screen.getByRole('button', { name: 'Voltar' }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
    const start = screen.getByRole('textbox', { name: 'Início' });
    const end = screen.getByRole('textbox', { name: 'Fim' });
    await userEvent.type(start, '15/09/2026 12:00:00');
    await userEvent.type(end, '14/09/2026 12:00:00');
    expect(
      screen.getByText('O fim deve ser posterior ao início.'),
    ).toBeTruthy();
    expect(
      (
        screen.getByRole('button', {
          name: 'Aplicar filtros',
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Limpar fim' }));
    expect(
      (
        screen.getByRole('button', {
          name: 'Aplicar filtros',
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
    await userEvent.click(
      screen.getByRole('button', { name: 'Aplicar filtros' }),
    );
    await waitFor(() => expect(screen.getByText(/Página 1/)).toBeTruthy());
    expect(list.mock.calls.at(-1)?.[0].occurred_from).toMatch(/Z$/);
  });
  it('deixa ambos os botões inativos quando não há registros', async () => {
    mountList(async () => ({
      ok: true,
      data: { items: [], next_cursor: null },
    }));
    await screen.findByText('Nenhum log nesta página.');
    expect(
      (screen.getByRole('button', { name: 'Voltar' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
  it('confirma a próxima página, reutiliza o cache e volta sem requisição duplicada', async () => {
    const second = {
      ...sample,
      id: '66f96a0de4b0a1b2c3d4e5f6',
      message: 'Fluxo continuado na página 2',
    };
    const list = vi.fn(async (query: LogQuery) => ({
      ok: true as const,
      data: query.cursor
        ? { items: [second], next_cursor: null }
        : { items: [sample], next_cursor: 'cursor-2' },
    }));
    mountList(list);
    await screen.findByRole('button', { name: /Falha ao cobrar/ });
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
    expect(
      (screen.getByRole('button', { name: 'Voltar' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Próxima' }));
    await screen.findByRole('button', { name: /Fluxo continuado na página 2/ });
    expect(
      (screen.getByRole('button', { name: 'Voltar' }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
    expect(
      (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Voltar' }));
    await screen.findByRole('button', { name: /Falha ao cobrar/ });
    expect(list).toHaveBeenCalledTimes(2);
  });
  it('não navega para cursor que devolve página vazia', async () => {
    const list = vi.fn(async (query: LogQuery) => ({
      ok: true as const,
      data: query.cursor
        ? { items: [], next_cursor: null }
        : { items: [sample], next_cursor: 'phantom' },
    }));
    mountList(list);
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
    expect(
      (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(screen.getByText(/Página 1/)).toBeTruthy();
  });
  it('reinicia o índice ao alterar e limpar filtros numa página avançada', async () => {
    const second = {
      ...sample,
      id: '66f96a0de4b0a1b2c3d4e5f6',
      message: 'Página avançada',
    };
    const list = vi.fn(async (query: LogQuery) => ({
      ok: true as const,
      data: query.tags?.length
        ? { items: [], next_cursor: null }
        : query.cursor
          ? { items: [second], next_cursor: null }
          : { items: [sample], next_cursor: 'cursor-2' },
    }));
    mountList(list);
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Próxima' }));
    await screen.findByRole('button', { name: /Página avançada/ });
    await userEvent.type(
      screen.getByRole('combobox', { name: 'Tags' }),
      'feature:sem-resultados',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Aplicar filtros' }),
    );
    await screen.findByText('Nenhum log nesta página.');
    expect(screen.getByText(/Página 1/)).toBeTruthy();
    expect(
      (screen.getByRole('button', { name: 'Voltar' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await userEvent.click(
      screen.getByRole('button', { name: 'Limpar filtros' }),
    );
    await screen.findByRole('button', { name: /Falha ao cobrar/ });
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Próxima' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
    expect(screen.getByText(/Página 1/)).toBeTruthy();
  });
});
