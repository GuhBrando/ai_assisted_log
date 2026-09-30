import type { LogQuery, LogRead } from '../contracts';

export const levels = [
  'TRACE',
  'DEBUG',
  'INFORMATION',
  'WARNING',
  'ERROR',
  'CRITICAL',
] as const;
export const levelNames = [
  'Trace',
  'Debug',
  'Info',
  'Warning',
  'Error',
  'Critical',
] as const;

const pad2 = (number: number): string => String(number).padStart(2, '0');

export function formatDateTime(date: Date): string {
  return `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}/${date.getFullYear()} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

export function parseDateTime(value: string): Date | null {
  const match = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2}):(\d{2})$/.exec(
    value,
  );
  if (!match) return null;
  const [, day, month, year, hour, minute, second] = match.map(Number);
  const date = new Date(year, month - 1, day, hour, minute, second);
  return date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day &&
    date.getHours() === hour &&
    date.getMinutes() === minute &&
    date.getSeconds() === second
    ? date
    : null;
}

export function displayTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : formatDateTime(date);
}

export function draftToQuery(
  draft: {
    application_id: string;
    min_level: string;
    correlation_id: string;
    occurred_from: string;
    occurred_to: string;
    tags: string;
  },
  limit = 50,
): LogQuery {
  const query: LogQuery = { limit };
  if (draft.application_id) query.application_id = draft.application_id;
  if (draft.min_level)
    query.min_level = Number(draft.min_level) as LogQuery['min_level'];
  if (draft.correlation_id.trim())
    query.correlation_id = draft.correlation_id.trim();
  if (draft.occurred_from) {
    const start = parseDateTime(draft.occurred_from);
    if (!start) throw new Error('Data e hora inicial inválidas.');
    query.occurred_from = start.toISOString();
  }
  if (draft.occurred_to) {
    const end = parseDateTime(draft.occurred_to);
    if (!end) throw new Error('Data e hora final inválidas.');
    query.occurred_to = end.toISOString();
  }
  if (
    query.occurred_from &&
    query.occurred_to &&
    query.occurred_to <= query.occurred_from
  )
    throw new Error('A data final deve ser posterior à inicial.');
  if (draft.tags.trim()) {
    const tags = [
      ...new Set(
        draft.tags
          .split(',')
          .map((tag) => tag.trim().toLowerCase())
          .filter(Boolean),
      ),
    ];
    if (
      tags.length > 20 ||
      tags.some((tag) => tag.length > 100 || !/^[a-z0-9_-]+:\S+$/.test(tag))
    )
      throw new Error(
        'Use até 20 tags no formato chave:valor, separadas por vírgula.',
      );
    query.tags = tags;
  }
  return query;
}

export function matchesSearch(log: LogRead, input: string): boolean {
  const needle = input.trim().toLocaleLowerCase();
  if (!needle) return true;
  return [
    log.id,
    log.application_name,
    log.message,
    log.environment,
    log.correlation_id ?? '',
    ...log.tags,
    log.exception ?? '',
  ].some((text) => text.toLocaleLowerCase().includes(needle));
}

export function timeBuckets(logs: LogRead[], count = 16): number[] {
  const times = logs
    .map((log) => Date.parse(log.occurred_at))
    .filter(Number.isFinite);
  if (!times.length) return Array(count).fill(0) as number[];
  const min = Math.min(...times),
    max = Math.max(...times);
  const buckets = Array(count).fill(0) as number[];
  for (const time of times)
    buckets[
      max === min
        ? count - 1
        : Math.min(count - 1, Math.floor(((time - min) / (max - min)) * count))
    ]++;
  return buckets;
}
