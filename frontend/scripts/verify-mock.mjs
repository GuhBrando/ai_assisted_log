import assert from 'node:assert/strict';
import { createMockLogs, compareLogs } from './mock-data.mjs';

const base = 'http://127.0.0.1:4010';
const login = await fetch(`${base}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'ana@example.com',
    password: 'uma-senha-longa',
  }),
});
assert.equal(login.status, 200);
const { access_token: token } = await login.json();
const headers = { Authorization: `Bearer ${token}` };
async function get(path, params) {
  const url = new URL(path, base);
  if (params)
    for (const [key, value] of Object.entries(params)) {
      for (const item of Array.isArray(value) ? value : [value])
        url.searchParams.append(key, item);
    }
  const response = await fetch(url, { headers });
  assert.equal(response.status, 200, `${url} respondeu ${response.status}`);
  return response.json();
}
function ordered(items) {
  return items.every(
    (item, index) => index === 0 || compareLogs(items[index - 1], item) <= 0,
  );
}

const all = createMockLogs();
const first = await get('/logs', { limit: '50' });
assert.equal(first.items.length, 50);
assert(ordered(first.items));
assert(first.next_cursor);
const second = await get('/logs', { limit: '50', cursor: first.next_cursor });
assert.equal(second.items.length, 50);
assert.notEqual(second.items[0].id, first.items[0].id);
const seen = new Set([...first.items, ...second.items].map((log) => log.id));
let cursor = second.next_cursor;
let pages = 2;
while (cursor) {
  const next = await get('/logs', { limit: '50', cursor });
  assert(next.items.length > 0 && next.items.length <= 50);
  assert(ordered(next.items));
  for (const log of next.items) {
    assert(!seen.has(log.id));
    seen.add(log.id);
  }
  cursor = next.next_cursor;
  pages++;
}
assert.equal(seen.size, 1600);
assert.equal(pages, 32);
const detail = await get(`/logs/${first.items[0].id}`);
assert.equal(detail.id, first.items[0].id);
const apps = await get('/applications');
assert.equal(apps.items.length, 3);

const from = all[650].occurred_at;
const to = all[100].occurred_at;
const correlation = all.find((log) => log.correlation_id)?.correlation_id;
assert(correlation);
const cases = [
  [{ occurred_from: from }, (log) => log.occurred_at >= from],
  [{ occurred_to: to }, (log) => log.occurred_at < to],
  [
    { occurred_from: from, occurred_to: to },
    (log) => log.occurred_at >= from && log.occurred_at < to,
  ],
  [{ tags: 'team:payments' }, (log) => log.tags.includes('team:payments')],
  [
    { tags: ['team:payments', 'feature:pix'] },
    (log) =>
      log.tags.includes('team:payments') && log.tags.includes('feature:pix'),
  ],
  [
    { occurred_from: from, occurred_to: to, tags: 'team:payments' },
    (log) =>
      log.occurred_at >= from &&
      log.occurred_at < to &&
      log.tags.includes('team:payments'),
  ],
  [
    { application_id: apps.items[0].id, min_level: '3' },
    (log) => log.application_id === apps.items[0].id && log.level >= 3,
  ],
  [
    { correlation_id: correlation },
    (log) => log.correlation_id === correlation,
  ],
];
for (const [params, predicate] of cases) {
  const page = await get('/logs', { limit: '50', ...params });
  assert(ordered(page.items));
  if (params.correlation_id) assert(page.items.length > 0);
  assert(page.items.every(predicate), JSON.stringify(params));
}
const one = await get('/logs', {
  occurred_from: all[0].occurred_at,
  occurred_to: new Date(Date.parse(all[0].occurred_at) + 1).toISOString(),
  application_id: all[0].application_id,
});
assert.equal(one.items.length, 1);
assert.equal(one.next_cursor, null);
const none = await get('/logs', { tags: 'feature:does-not-exist' });
assert.deepEqual(none, { items: [], next_cursor: null });
console.log(
  JSON.stringify({
    checked: 1600,
    pages,
    filterCases: cases.length + 2,
    result: 'ok',
  }),
);
