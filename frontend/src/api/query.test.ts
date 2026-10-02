import { describe, expect, it } from 'vitest';
import { parseLogQuery, queryString } from './query';

describe('consulta de logs', () => {
  it('repete tags e preserva o cursor opaco', () => {
    const parsed = parseLogQuery({
      tags: ['team:payments', 'feature:pix'],
      cursor: 'opaque+value=',
      min_level: 3,
      limit: 50,
    });
    const params = new URLSearchParams(queryString(parsed));
    expect(params.getAll('tags')).toEqual(['team:payments', 'feature:pix']);
    expect(params.get('cursor')).toBe('opaque+value=');
    expect(params.get('min_level')).toBe('3');
  });
  it('recusa campos fora do contrato e período invertido', () => {
    expect(() => parseLogQuery({ customer_id: 'abc' })).toThrow(
      'Filtro não permitido',
    );
    expect(() =>
      parseLogQuery({
        occurred_from: '2026-09-29T10:00:00Z',
        occurred_to: '2026-09-29T10:00:00Z',
      }),
    ).toThrow('posterior');
    expect(() => parseLogQuery({ limit: 101 })).toThrow('Limite');
  });
});
