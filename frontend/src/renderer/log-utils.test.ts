import { describe, expect, it } from 'vitest';
import type { LogRead } from '../contracts';
import { draftToQuery, matchesSearch, timeBuckets } from './log-utils';

const empty = {
  application_id: '',
  min_level: '',
  correlation_id: '',
  occurred_from: '',
  occurred_to: '',
  tags: '',
};
const log = {
  id: '66f8b112e4b0a1b2c3d4e5f9',
  application_name: 'Checkout',
  message: 'Falha ao cobrar',
  environment: 'prod',
  correlation_id: null,
  tags: ['team:payments'],
  exception: null,
  occurred_at: '2026-09-29T10:00:00Z',
} as LogRead;

describe('filtros e indicadores locais', () => {
  it('converte período local para UTC, normaliza tags e rejeita fim anterior', () => {
    const query = draftToQuery({
      ...empty,
      occurred_from: '2026-09-29T10:00',
      occurred_to: '2026-09-29T11:00',
      tags: ' Team:Payments, feature:PIX, team:payments',
    });
    expect(query.occurred_from).toMatch(/Z$/);
    expect(query.tags).toEqual(['team:payments', 'feature:pix']);
    expect(() =>
      draftToQuery({
        ...empty,
        occurred_from: '2026-09-29T11:00',
        occurred_to: '2026-09-29T10:00',
      }),
    ).toThrow('posterior');
  });
  it('busca texto somente nos registros recebidos da página', () => {
    expect(matchesSearch(log, 'cobrar')).toBe(true);
    expect(matchesSearch(log, 'outro cliente')).toBe(false);
    expect(timeBuckets([log]).reduce((a, b) => a + b, 0)).toBe(1);
  });
});
