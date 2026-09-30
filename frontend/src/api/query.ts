import type { LogQuery } from '../contracts';

const objectId = /^[a-f\d]{24}$/i;
const uuid = /^[a-f\d]{8}(?:-[a-f\d]{4}){3}-[a-f\d]{12}$/i;
const tag = /^[a-z0-9_-]+:\S+$/;
const queryKeys = new Set([
  'application_id',
  'min_level',
  'correlation_id',
  'occurred_from',
  'occurred_to',
  'tags',
  'limit',
  'cursor',
]);

export function parseLogQuery(value: unknown): LogQuery {
  if (typeof value !== 'object' || value === null || Array.isArray(value))
    throw new Error('Filtros inválidos.');
  const input = value as Record<string, unknown>;
  if (Object.keys(input).some((key) => !queryKeys.has(key)))
    throw new Error('Filtro não permitido.');
  const output: LogQuery = {};
  if (input.application_id !== undefined) {
    if (
      typeof input.application_id !== 'string' ||
      !objectId.test(input.application_id)
    )
      throw new Error('Aplicação inválida.');
    output.application_id = input.application_id;
  }
  if (input.min_level !== undefined) {
    if (
      !Number.isInteger(input.min_level) ||
      Number(input.min_level) < 0 ||
      Number(input.min_level) > 5
    )
      throw new Error('Nível inválido.');
    output.min_level = input.min_level as LogQuery['min_level'];
  }
  if (input.correlation_id !== undefined) {
    if (
      typeof input.correlation_id !== 'string' ||
      !uuid.test(input.correlation_id)
    )
      throw new Error('Correlation ID inválido.');
    output.correlation_id = input.correlation_id;
  }
  for (const key of ['occurred_from', 'occurred_to'] as const) {
    const date = input[key];
    if (date !== undefined) {
      if (
        typeof date !== 'string' ||
        !/\d{4}-\d{2}-\d{2}T/.test(date) ||
        !Number.isFinite(Date.parse(date))
      )
        throw new Error('Data inválida.');
      output[key] = date;
    }
  }
  if (
    output.occurred_from &&
    output.occurred_to &&
    Date.parse(output.occurred_to) <= Date.parse(output.occurred_from)
  )
    throw new Error('O fim deve ser posterior ao início.');
  if (input.tags !== undefined) {
    if (
      !Array.isArray(input.tags) ||
      input.tags.length > 20 ||
      input.tags.some(
        (item) =>
          typeof item !== 'string' || item.length > 100 || !tag.test(item),
      )
    )
      throw new Error('Tags inválidas.');
    output.tags = input.tags as string[];
  }
  if (input.limit !== undefined) {
    if (
      !Number.isInteger(input.limit) ||
      Number(input.limit) < 1 ||
      Number(input.limit) > 100
    )
      throw new Error('Limite inválido.');
    output.limit = input.limit as number;
  }
  if (input.cursor !== undefined) {
    if (
      typeof input.cursor !== 'string' ||
      input.cursor.length === 0 ||
      input.cursor.length > 4096
    )
      throw new Error('Cursor inválido.');
    output.cursor = input.cursor;
  }
  return output;
}

export function queryString(query: LogQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue;
    if (Array.isArray(value))
      value.forEach((tagValue) => params.append(key, tagValue));
    else params.set(key, String(value));
  }
  return params.toString();
}

export function isObjectId(value: unknown): value is string {
  return typeof value === 'string' && objectId.test(value);
}
