// @vitest-environment jsdom
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('investigação visual', () => {
  it('mostra dados resumidos e busca o detalhe completo com stack trace', async () => {
    const getLog = vi.fn(async () => ({ ok: true as const, data: sample }));
    const api = {
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
    await userEvent.click(row);
    await waitFor(() => expect(getLog).toHaveBeenCalledWith(sample.id));
    expect(
      await screen.findByText(/ValueError: pagamento recusado/),
    ).toBeTruthy();
    expect(screen.getByText(sample.correlation_id!)).toBeTruthy();
  });
});
