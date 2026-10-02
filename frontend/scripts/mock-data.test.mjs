import { describe, expect, it } from 'vitest';
import { createMockLogs, listMockLogs, compareLogs } from './mock-data.mjs';

const all = createMockLogs();
function page(query = {}) {
  return listMockLogs(all, new URLSearchParams(query));
}

describe('massa de investigação do Prism', () => {
  it('tem 1.600 registros coerentes, intervalos vazios e fluxos intercalados entre páginas', () => {
    expect(all).toHaveLength(1600);
    expect(
      all.filter((log) => log.correlation_id === null).length,
    ).toBeGreaterThan(200);
    expect(
      new Set(all.map((log) => log.occurred_at.slice(0, 10))).size,
    ).toBeGreaterThan(5);
    expect(all.some((log) => log.message.length > 150)).toBe(true);
    expect(all.some((log) => log.tags.length >= 3)).toBe(true);
    const sameSeconds = new Map();
    for (const log of all)
      sameSeconds.set(
        log.occurred_at.slice(0, 19),
        (sameSeconds.get(log.occurred_at.slice(0, 19)) ?? 0) + 1,
      );
    expect([...sameSeconds.values()].some((count) => count >= 2)).toBe(true);
    const pages = [];
    let cursor = null;
    do {
      const result = page(cursor ? { cursor, limit: '50' } : { limit: '50' });
      pages.push(result);
      cursor = result.next_cursor;
    } while (cursor);
    expect(pages).toHaveLength(32);
    expect(pages.at(-1).next_cursor).toBeNull();
    expect(
      pages.every(
        (result) => result.items.length > 0 && result.items.length <= 50,
      ),
    ).toBe(true);
    const ids = pages.flatMap((result) => result.items.map((log) => log.id));
    expect(new Set(ids).size).toBe(1600);
    const flowPages = new Map();
    pages.forEach((result, index) =>
      result.items.forEach((log) => {
        if (log.correlation_id) {
          const seen = flowPages.get(log.correlation_id) ?? new Set();
          seen.add(index);
          flowPages.set(log.correlation_id, seen);
        }
      }),
    );
    expect([...flowPages.values()].some((seen) => seen.size > 1)).toBe(true);
    expect(
      all.every(
        (log, index) => index === 0 || compareLogs(all[index - 1], log) <= 0,
      ),
    ).toBe(true);
  });
  it('combina início, fim, tags e página; suporta um ou nenhum resultado', () => {
    const from = all[650].occurred_at,
      to = all[100].occurred_at;
    const onlyFrom = page({ occurred_from: from });
    const onlyTo = page({ occurred_to: to });
    const both = page({ occurred_from: from, occurred_to: to });
    const tags = page({ tags: 'team:payments' });
    const combined = page({
      occurred_from: from,
      occurred_to: to,
      tags: 'team:payments',
    });
    expect(onlyFrom.items.every((log) => log.occurred_at >= from)).toBe(true);
    expect(onlyTo.items.every((log) => log.occurred_at < to)).toBe(true);
    expect(
      both.items.every(
        (log) => log.occurred_at >= from && log.occurred_at < to,
      ),
    ).toBe(true);
    expect(tags.items.every((log) => log.tags.includes('team:payments'))).toBe(
      true,
    );
    expect(
      combined.items.every(
        (log) =>
          log.occurred_at >= from &&
          log.occurred_at < to &&
          log.tags.includes('team:payments'),
      ),
    ).toBe(true);
    const one = page({
      occurred_from: all[0].occurred_at,
      occurred_to: new Date(Date.parse(all[0].occurred_at) + 1).toISOString(),
      application_id: all[0].application_id,
    });
    expect(one.items).toHaveLength(1);
    expect(one.next_cursor).toBeNull();
    expect(page({ tags: 'feature:does-not-exist' }).items).toHaveLength(0);
    expect(page({ tags: 'feature:does-not-exist' }).next_cursor).toBeNull();
  });
});
