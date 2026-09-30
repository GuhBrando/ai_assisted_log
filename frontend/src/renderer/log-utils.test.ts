import { describe, expect, it } from 'vitest';
import type { LogRead } from '../contracts';
import {
  displayTime,
  draftToQuery,
  formatDateTime,
  matchesSearch,
  parseDateTime,
  timeBuckets,
} from './log-utils';

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

describe('data/hora e filtros', () => {
  it('usa DD/MM/AAAA HH:MM:SS e rejeita dia ou horário inexistentes', () => {
    const date = parseDateTime('29/09/2026 10:03:07');
    expect(date).not.toBeNull();
    expect(formatDateTime(date!)).toBe('29/09/2026 10:03:07');
    expect(displayTime('2026-09-29T10:03:07Z')).toMatch(
      /^\d{2}\/\d{2}\/2026 \d{2}:\d{2}:\d{2}$/,
    );
    expect(parseDateTime('31/02/2026 10:00:00')).toBeNull();
    expect(parseDateTime('29/09/2026 25:00:00')).toBeNull();
    expect(parseDateTime('2026-09-29T10:00')).toBeNull();
  });
  it('aceita só Início, só Fim e ambos; normaliza tags e impede período invertido', () => {
    const from = '29/09/2026 10:00:00',
      to = '29/09/2026 11:00:00';
    expect(
      draftToQuery({ ...empty, occurred_from: from }).occurred_from,
    ).toMatch(/Z$/);
    expect(draftToQuery({ ...empty, occurred_to: to }).occurred_to).toMatch(
      /Z$/,
    );
    const query = draftToQuery({
      ...empty,
      occurred_from: from,
      occurred_to: to,
      tags: ' Team:Payments, feature:PIX, team:payments',
    });
    expect(query.tags).toEqual(['team:payments', 'feature:pix']);
    expect(
      Date.parse(query.occurred_to!) - Date.parse(query.occurred_from!),
    ).toBe(3600000);
    expect(() =>
      draftToQuery({ ...empty, occurred_from: to, occurred_to: from }),
    ).toThrow('posterior');
    expect(() =>
      draftToQuery({ ...empty, occurred_from: '31/02/2026 10:00:00' }),
    ).toThrow('inválidas');
    expect(draftToQuery(empty)).toEqual({ limit: 50 });
  });
  it('busca texto só na página recebida e conta o período dela', () => {
    expect(matchesSearch(log, 'cobrar')).toBe(true);
    expect(matchesSearch(log, 'outro cliente')).toBe(false);
    expect(timeBuckets([log]).reduce((a, b) => a + b, 0)).toBe(1);
  });
});
