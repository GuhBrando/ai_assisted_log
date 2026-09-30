import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { LogQuery, LogRead } from '../contracts';
import {
  displayTime,
  draftToQuery,
  levelNames,
  levels,
  matchesSearch,
  timeBuckets,
} from './log-utils';

type Draft = {
  application_id: string;
  min_level: string;
  correlation_id: string;
  occurred_from: string;
  occurred_to: string;
  tags: string;
};
const emptyDraft: Draft = {
  application_id: '',
  min_level: '',
  correlation_id: '',
  occurred_from: '',
  occurred_to: '',
  tags: '',
};

function requireData<T>(
  result:
    | { ok: true; data: T }
    | { ok: false; error: { message: string; status?: number } },
  onExpired: () => void,
): T {
  if (result.ok) return result.data;
  if (result.error.status === 401) onExpired();
  throw new Error(result.error.message);
}

function Summary({ logs }: { logs: LogRead[] }): React.JSX.Element {
  const counts = levels.map(
    (_, level) => logs.filter((log) => log.level === level).length,
  );
  const buckets = timeBuckets(logs);
  const tallest = Math.max(1, ...buckets);
  return (
    <section className="summary" aria-label="Resumo da página">
      <div className="summary-heading">
        <div>
          <span className="eyebrow">VISÃO DA PÁGINA</span>
          <h2>Volume e severidade</h2>
        </div>
        <span className="summary-note">
          Somente os {logs.length} registros carregados
        </span>
      </div>
      <div className="summary-body">
        <div className="stats">
          <div className="stat total">
            <strong>{logs.length}</strong>
            <span>Registros</span>
          </div>
          {levels.map((level, index) => (
            <div className="stat" key={level}>
              <strong className={`tone-${index}`}>{counts[index]}</strong>
              <span>{levelNames[index]}</span>
            </div>
          ))}
        </div>
        <div
          className="spark"
          role="img"
          aria-label="Distribuição temporal dos registros desta página, da ocorrência mais antiga à mais recente"
        >
          {buckets.map((value, index) => (
            <div
              key={index}
              className="spark-bar"
              style={{ height: `${Math.max(6, (value / tallest) * 100)}%` }}
              title={`${value} registros no intervalo ${index + 1}`}
            />
          ))}
        </div>
      </div>
      <div className="spark-labels">
        <span>Mais antigos nesta página</span>
        <span>Mais recentes nesta página</span>
      </div>
    </section>
  );
}

function Detail({
  id,
  onClose,
  onCorrelation,
  onExpired,
}: {
  id: string;
  onClose: () => void;
  onCorrelation: (id: string) => void;
  onExpired: () => void;
}): React.JSX.Element {
  const detail = useQuery({
    queryKey: ['detail', id],
    queryFn: async () => requireData(await window.logApi.getLog(id), onExpired),
    staleTime: 60000,
  });
  const log = detail.data;
  return (
    <aside className="detail" aria-label="Detalhes do log">
      <div className="detail-header">
        <div>
          <span className="eyebrow">INVESTIGAÇÃO</span>
          <h2>Detalhes do evento</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Fechar detalhes"
        >
          ×
        </button>
      </div>
      {detail.isPending && <p className="muted">Carregando detalhes…</p>}
      {detail.isError && (
        <p className="form-error" role="alert">
          {detail.error.message}
        </p>
      )}
      {log && (
        <div className="detail-content">
          <div className="detail-lead">
            <span className={`level-pill tone-${log.level}`}>
              {levels[log.level]}
            </span>
            <h3>{log.message}</h3>
          </div>
          <dl className="metadata">
            <dt>Ocorrido em</dt>
            <dd>{displayTime(log.occurred_at)}</dd>
            <dt>Recebido em</dt>
            <dd>{displayTime(log.received_at)}</dd>
            <dt>Expira em</dt>
            <dd>{displayTime(log.expire_at)}</dd>
            <dt>Aplicação</dt>
            <dd>{log.application_name}</dd>
            <dt>Ambiente</dt>
            <dd>{log.environment}</dd>
            <dt>Log ID</dt>
            <dd className="mono break">
              {log.id}{' '}
              <button
                className="text-button"
                onClick={() => void window.logApi.copyLogId(log.id)}
              >
                Copiar
              </button>
            </dd>
            <dt>Application ID</dt>
            <dd className="mono break">{log.application_id}</dd>
            <dt>Correlation ID</dt>
            <dd className="mono break">
              {log.correlation_id ? (
                <>
                  <span>{log.correlation_id}</span>
                  <button
                    className="text-button"
                    onClick={() => onCorrelation(log.correlation_id!)}
                  >
                    Filtrar fluxo
                  </button>
                </>
              ) : (
                '—'
              )}
            </dd>
          </dl>
          <div className="detail-section">
            <h4>Tags</h4>
            <div className="tag-list">
              {log.tags.length ? (
                log.tags.map((tag) => (
                  <span className="tag" key={tag}>
                    {tag}
                  </span>
                ))
              ) : (
                <span className="muted">Nenhuma tag</span>
              )}
            </div>
          </div>
          <details
            className="detail-section"
            open={Boolean(log.information_data)}
          >
            <summary>Informações estruturadas</summary>
            {log.information_data ? (
              <pre>{JSON.stringify(log.information_data, null, 2)}</pre>
            ) : (
              <p className="muted">Sem informações adicionais.</p>
            )}
          </details>
          <div className="detail-section">
            <h4>Exceção e stack trace</h4>
            {log.exception ? (
              <pre className="stacktrace">{log.exception}</pre>
            ) : (
              <p className="muted">Nenhuma exceção registrada.</p>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}

export function Logs({
  onLogout,
  onExpired,
}: {
  onLogout: () => void;
  onExpired: () => void;
}): React.JSX.Element {
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [query, setQuery] = useState<LogQuery>({ limit: 50 });
  const [filterError, setFilterError] = useState('');
  const [search, setSearch] = useState('');
  const [cursors, setCursors] = useState<Array<string | undefined>>([
    undefined,
  ]);
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const applications = useQuery({
    queryKey: ['applications'],
    queryFn: async () =>
      requireData(await window.logApi.listApplications(), onExpired),
    staleTime: 60000,
  });
  const cursor = cursors[pageIndex];
  const logs = useQuery({
    queryKey: ['logs', query, cursor],
    queryFn: async () =>
      requireData(
        await window.logApi.listLogs({ ...query, cursor }),
        onExpired,
      ),
    placeholderData: (previous) => previous,
  });
  const items = logs.data?.items ?? [];
  const visible = useMemo(
    () => items.filter((log) => matchesSearch(log, search)),
    [items, search],
  );
  useEffect(() => {
    if (selectedId && !items.some((log) => log.id === selectedId))
      setSelectedId(null);
  }, [items, selectedId]);
  function applyFilters(event?: React.FormEvent): void {
    event?.preventDefault();
    try {
      const next = draftToQuery(draft, query.limit);
      setQuery(next);
      setCursors([undefined]);
      setPageIndex(0);
      setSelectedId(null);
      setFilterError('');
    } catch (error) {
      setFilterError(
        error instanceof Error ? error.message : 'Filtros inválidos.',
      );
    }
  }
  function clearFilters(): void {
    setDraft(emptyDraft);
    setQuery({ limit: 50 });
    setCursors([undefined]);
    setPageIndex(0);
    setFilterError('');
    setSelectedId(null);
  }
  function setCorrelation(id: string): void {
    const next = { ...draft, correlation_id: id };
    setDraft(next);
    setQuery({ ...query, correlation_id: id, cursor: undefined });
    setCursors([undefined]);
    setPageIndex(0);
    setSelectedId(null);
  }
  function nextPage(): void {
    const next = logs.data?.next_cursor;
    if (!next) return;
    setCursors((current) => [...current.slice(0, pageIndex + 1), next]);
    setPageIndex(pageIndex + 1);
    setSelectedId(null);
  }
  const selected = selectedId !== null;
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-symbol">⌁</span>
          <span>LOG INSIGHT</span>
          <span className="topbar-divider" />
          <span className="topbar-context">Explorador de logs</span>
        </div>
        <div className="topbar-actions">
          <span className="connection-dot" />
          <span className="connection-label">
            {process.env.NODE_ENV === 'development'
              ? 'Prism · 4010'
              : 'API local · 8000'}
          </span>
          <button className="quiet-button" onClick={onLogout}>
            Sair
          </button>
        </div>
      </header>
      <main className="workspace">
        <div className="page-heading">
          <div>
            <span className="eyebrow">OBSERVABILIDADE / LOGS</span>
            <h1>Investigue com contexto.</h1>
            <p>
              Filtre eventos, identifique picos e acompanhe um fluxo pela
              correlação.
            </p>
          </div>
          <button
            className="quiet-button refresh"
            onClick={() => void logs.refetch()}
            disabled={logs.isFetching}
          >
            ↻ Atualizar página
          </button>
        </div>
        <form className="filters" onSubmit={applyFilters}>
          <div className="section-heading">
            <span>Filtros</span>
            <span className="muted">Os filtros são combinados com E</span>
          </div>
          <div className="filter-grid">
            <label>
              Aplicação
              <select
                value={draft.application_id}
                onChange={(event) =>
                  setDraft({ ...draft, application_id: event.target.value })
                }
              >
                <option value="">Todas as aplicações</option>
                {applications.data?.items.map((app) => (
                  <option value={app.id} key={app.id}>
                    {app.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Nível mínimo
              <select
                value={draft.min_level}
                onChange={(event) =>
                  setDraft({ ...draft, min_level: event.target.value })
                }
              >
                <option value="">Todos os níveis</option>
                {levels.map((level, index) => (
                  <option value={index} key={level}>
                    {levelNames[index]} e acima
                  </option>
                ))}
              </select>
            </label>
            <label>
              Início <span className="field-hint">inclusive</span>
              <input
                type="datetime-local"
                value={draft.occurred_from}
                onChange={(event) =>
                  setDraft({ ...draft, occurred_from: event.target.value })
                }
              />
            </label>
            <label>
              Fim <span className="field-hint">exclusivo</span>
              <input
                type="datetime-local"
                value={draft.occurred_to}
                onChange={(event) =>
                  setDraft({ ...draft, occurred_to: event.target.value })
                }
              />
            </label>
            <label className="wide-field">
              Correlation ID
              <input
                value={draft.correlation_id}
                onChange={(event) =>
                  setDraft({ ...draft, correlation_id: event.target.value })
                }
                placeholder="UUID do fluxo"
              />
            </label>
            <label className="wide-field">
              Tags <span className="field-hint">separadas por vírgula</span>
              <input
                value={draft.tags}
                onChange={(event) =>
                  setDraft({ ...draft, tags: event.target.value })
                }
                placeholder="team:payments, feature:pix"
              />
            </label>
          </div>
          {filterError && (
            <p className="form-error filter-error" role="alert">
              {filterError}
            </p>
          )}
          {applications.isError && (
            <p className="form-error filter-error" role="alert">
              Aplicações: {applications.error.message}
            </p>
          )}
          <div className="filter-actions">
            <button
              className="quiet-button"
              type="button"
              onClick={clearFilters}
            >
              Limpar filtros
            </button>
            <button className="primary-button" type="submit">
              Aplicar filtros
            </button>
          </div>
        </form>
        <Summary logs={items} />
        <section className="logs-section">
          <div className="section-heading list-heading">
            <div>
              <span>Eventos</span>
              <span className="list-count">
                {visible.length} nesta página{search ? ' após busca' : ''}
              </span>
            </div>
            <div className="list-tools">
              <label className="search-label">
                <span className="sr-only">Buscar na página carregada</span>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar nesta página"
                />
              </label>
              <span className="page-scope">
                Busca somente na página carregada
              </span>
            </div>
          </div>
          <div className={`logs-layout ${selected ? 'with-detail' : ''}`}>
            <div className="log-list" aria-label="Lista de logs">
              {logs.isPending && (
                <div className="empty-state">Carregando logs…</div>
              )}
              {logs.isError && (
                <div className="empty-state error-state" role="alert">
                  <strong>Não foi possível carregar os logs.</strong>
                  <span>{logs.error.message}</span>
                  <button
                    className="quiet-button"
                    onClick={() => void logs.refetch()}
                  >
                    Tentar novamente
                  </button>
                </div>
              )}
              {!logs.isPending && !logs.isError && visible.length === 0 && (
                <div className="empty-state">
                  <strong>
                    {items.length === 0
                      ? 'Nenhum log nesta página.'
                      : 'Nenhum log corresponde à busca nesta página.'}
                  </strong>
                  <span>Ajuste os filtros ou a busca para continuar.</span>
                </div>
              )}
              {visible.map((log) => (
                <button
                  type="button"
                  className={`log-row ${selectedId === log.id ? 'selected' : ''}`}
                  key={log.id}
                  onClick={() => setSelectedId(log.id)}
                >
                  <span className="log-time mono">
                    {displayTime(log.occurred_at)}
                  </span>
                  <span className={`level-pill tone-${log.level}`}>
                    {levels[log.level]}
                  </span>
                  <span className="log-main">
                    <strong>{log.message}</strong>
                    <span className="log-secondary">
                      <span>{log.application_name}</span>
                      <span>· {log.environment}</span>
                      {log.tags.slice(0, 2).map((tag) => (
                        <span className="tag mini" key={tag}>
                          {tag}
                        </span>
                      ))}
                      {log.tags.length > 2 && (
                        <span>+{log.tags.length - 2} tags</span>
                      )}
                      {log.exception && (
                        <span className="exception-flag">Exceção</span>
                      )}
                    </span>
                  </span>
                  <span className="row-arrow">›</span>
                </button>
              ))}
            </div>
            {selectedId && (
              <Detail
                id={selectedId}
                onClose={() => setSelectedId(null)}
                onCorrelation={setCorrelation}
                onExpired={onExpired}
              />
            )}
          </div>
          <div className="pagination">
            <span>
              Página {pageIndex + 1} · até {query.limit ?? 50} registros por
              página · {items.length} carregados
            </span>
            <div>
              <button
                className="quiet-button"
                disabled={pageIndex === 0 || logs.isFetching}
                onClick={() => {
                  setPageIndex(pageIndex - 1);
                  setSelectedId(null);
                }}
              >
                Anterior
              </button>
              <button
                className="quiet-button"
                disabled={!logs.data?.next_cursor || logs.isFetching}
                onClick={nextPage}
              >
                Próxima
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
