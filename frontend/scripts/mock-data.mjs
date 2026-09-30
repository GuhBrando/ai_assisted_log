import { createHash } from 'node:crypto';

export const applications = [
  {
    id: '66f8b112e4b0a1b2c3d4e5f1',
    name: 'Checkout',
    tags: ['team:payments'],
    api_keys: [],
    created_at: '2026-08-01T09:00:00.000Z',
  },
  {
    id: '66f8b112e4b0a1b2c3d4e5f2',
    name: 'Identity',
    tags: ['team:platform'],
    api_keys: [],
    created_at: '2026-08-01T09:00:00.000Z',
  },
  {
    id: '66f8b112e4b0a1b2c3d4e5f3',
    name: 'Notifications',
    tags: ['team:messaging'],
    api_keys: [],
    created_at: '2026-08-01T09:00:00.000Z',
  },
];

function randomFactory(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function correlationFor(index) {
  const hex = createHash('sha256').update(`mock-flow-${index}`).digest('hex');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
}

const flows = [
  {
    name: 'success',
    steps: [
      [2, 'Operação iniciada'],
      [1, 'Entrada validada'],
      [2, 'Processamento iniciado'],
      [1, 'Chamada externa enviada'],
      [2, 'Resposta recebida'],
      [2, 'Operação concluída'],
    ],
  },
  {
    name: 'error',
    steps: [
      [2, 'Operação iniciada'],
      [1, 'Entrada validada'],
      [2, 'Chamada externa enviada'],
      [4, 'Falha na chamada externa'],
    ],
  },
  {
    name: 'retry',
    steps: [
      [2, 'Operação iniciada'],
      [2, 'Processamento iniciado'],
      [4, 'Timeout na primeira tentativa'],
      [3, 'Retry agendado'],
      [2, 'Resposta recebida após retry'],
      [2, 'Operação concluída'],
    ],
  },
  {
    name: 'attempts',
    steps: [
      [2, 'Operação iniciada'],
      [1, 'Tentativa 1 iniciada'],
      [3, 'Tentativa 1 sem resposta'],
      [1, 'Tentativa 2 iniciada'],
      [4, 'Tentativa 2 falhou'],
      [1, 'Tentativa 3 iniciada'],
      [2, 'Tentativa 3 concluída'],
      [2, 'Operação concluída'],
    ],
  },
  {
    name: 'short',
    steps: [
      [2, 'Operação iniciada'],
      [2, 'Operação concluída'],
    ],
  },
  {
    name: 'long',
    steps: [
      [2, 'Operação iniciada'],
      [1, 'Contexto carregado'],
      [1, 'Permissões validadas'],
      [2, 'Fila consultada'],
      [1, 'Payload preparado'],
      [2, 'Chamada externa enviada'],
      [1, 'Aguardando resposta'],
      [3, 'Resposta lenta'],
      [2, 'Resposta recebida'],
      [1, 'Resultado persistido'],
      [2, 'Notificação emitida'],
      [2, 'Operação concluída'],
    ],
  },
];
const activeDays = [1, 2, 3, 7, 11, 12, 18, 25, 26, 29];
const features = [
  'feature:pix',
  'feature:login',
  'feature:email',
  'feature:webhook',
];

export function createMockLogs(count = 1600) {
  const random = randomFactory(29092026);
  const items = [];
  let serial = 0;
  function add({
    application,
    correlation_id,
    level,
    message,
    occurredMs,
    tags,
    exception = null,
    information_data = null,
  }) {
    serial++;
    const occurred = new Date(occurredMs);
    const received = new Date(occurredMs + 200 + Math.floor(random() * 2400));
    items.push({
      id: `66f900000000000000${serial.toString(16).padStart(6, '0')}`,
      application_id: application.id,
      application_name: application.name,
      correlation_id,
      level,
      message,
      exception,
      environment: serial % 8 === 0 ? 'staging' : 'prod',
      information_data,
      tags: [...new Set([...application.tags, ...tags])],
      occurred_at: occurred.toISOString(),
      received_at: received.toISOString(),
      expire_at: new Date(received.getTime() + 30 * 86400000).toISOString(),
    });
  }
  for (
    let flowIndex = 0;
    items.length < Math.floor(count * 0.82);
    flowIndex++
  ) {
    const flow = flows[flowIndex % flows.length];
    const application = applications[flowIndex % applications.length];
    const day = activeDays[Math.floor(random() * activeDays.length)];
    const hour = [9, 10, 10, 11, 14, 14, 17][Math.floor(random() * 7)];
    const minute = Math.floor(random() * 60);
    const second = Math.floor(random() * 60);
    const base = Date.UTC(2026, 8, day, hour, minute, second);
    const correlation_id = correlationFor(flowIndex);
    const feature = features[flowIndex % features.length];
    let offset = 0;
    flow.steps.forEach(([level, step], stepIndex) => {
      if (stepIndex > 0)
        offset +=
          flow.name === 'long'
            ? 1000 + Math.floor(random() * 12000)
            : 100 + Math.floor(random() * 2200);
      const isError = level >= 4;
      add({
        application,
        correlation_id,
        level,
        message:
          flowIndex % 11 === 0 && stepIndex === 2
            ? `${step}: a operação aguardou a confirmação do serviço externo e continuou com o mesmo identificador de correlação para permitir acompanhar todos os eventos, inclusive quando ocorrer uma nova tentativa.`
            : `${step} · ${flow.name} #${flowIndex + 1}`,
        occurredMs: base + offset,
        tags: [
          feature,
          ...(flow.name === 'retry' || flow.name === 'attempts'
            ? ['flow:retry']
            : []),
          ...(flowIndex % 5 === 0 ? ['region:sa-east-1'] : []),
        ],
        exception: isError
          ? `ExternalServiceError: ${step}\n  at processarOperacao (service.ts:42)\n  at chamarServico (client.ts:18)`
          : null,
        information_data:
          stepIndex % 3 === 0
            ? {
                flow: flow.name,
                step: stepIndex + 1,
                attempt:
                  flow.name === 'attempts' ? Math.ceil(stepIndex / 2) : 1,
              }
            : null,
      });
    });
  }
  while (items.length < count) {
    const isolated = items.length;
    const day = activeDays[Math.floor(random() * activeDays.length)];
    const application = applications[isolated % applications.length];
    add({
      application,
      correlation_id: null,
      level: [0, 1, 2, 2, 3, 4, 5][isolated % 7],
      message:
        isolated % 9 === 0
          ? 'Evento isolado com mensagem extensa: o serviço respondeu após diversas verificações internas, incluindo validação de dependências, confirmação de estado e escrita de dados para análise posterior.'
          : `Evento isolado #${isolated + 1}`,
      occurredMs: Date.UTC(
        2026,
        8,
        day,
        6 + Math.floor(random() * 16),
        Math.floor(random() * 60),
        Math.floor(random() * 60),
      ),
      tags: [
        features[isolated % features.length],
        ...(isolated % 4 === 0 ? ['region:sa-east-1'] : []),
      ],
    });
  }
  return items.sort(compareLogs);
}

export function compareLogs(a, b) {
  return b.occurred_at.localeCompare(a.occurred_at) || b.id.localeCompare(a.id);
}

function decodeCursor(cursor) {
  if (!cursor) return null;
  try {
    const decoded = JSON.parse(
      Buffer.from(cursor, 'base64url').toString('utf8'),
    );
    if (
      typeof decoded.occurred_at !== 'string' ||
      typeof decoded.id !== 'string'
    )
      return null;
    return decoded;
  } catch {
    return null;
  }
}

export function listMockLogs(allLogs, params) {
  const application = params.get('application_id');
  const minLevel = params.get('min_level');
  const correlation = params.get('correlation_id');
  const from = params.get('occurred_from');
  const to = params.get('occurred_to');
  const tags = params.getAll('tags').map((tag) => tag.trim().toLowerCase());
  const cursor = decodeCursor(params.get('cursor'));
  const limit = Math.min(100, Math.max(1, Number(params.get('limit') ?? 50)));
  const filtered = allLogs.filter(
    (log) =>
      (!application || log.application_id === application) &&
      (minLevel === null || log.level >= Number(minLevel)) &&
      (!correlation || log.correlation_id === correlation) &&
      (!from || log.occurred_at >= from) &&
      (!to || log.occurred_at < to) &&
      tags.every((tag) => log.tags.includes(tag)) &&
      (!cursor ||
        log.occurred_at < cursor.occurred_at ||
        (log.occurred_at === cursor.occurred_at && log.id < cursor.id)),
  );
  const items = filtered.slice(0, limit);
  const last = items.at(-1);
  return {
    items,
    next_cursor:
      filtered.length > limit && last
        ? Buffer.from(
            JSON.stringify({ occurred_at: last.occurred_at, id: last.id }),
          ).toString('base64url')
        : null,
  };
}
