import type {
  ApplicationList,
  LogPage,
  LogQuery,
  LogRead,
  UserLogin,
} from '../contracts';
import { queryString } from './query';

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

export class ApiClient {
  private token: string | null = null;
  private expiresAt = 0;

  constructor(private readonly baseUrl: string) {}

  hasSession(): boolean {
    if (this.token && Date.now() < this.expiresAt) return true;
    this.logout();
    return false;
  }

  logout(): void {
    this.token = null;
    this.expiresAt = 0;
  }

  async login(credentials: UserLogin): Promise<void> {
    this.logout();
    const response = await this.request<{
      access_token: string;
      token_type: 'bearer';
      expires_in: number;
    }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify(credentials),
        headers: { 'Content-Type': 'application/json' },
      },
      false,
    );
    if (
      typeof response.access_token !== 'string' ||
      response.token_type !== 'bearer' ||
      !Number.isInteger(response.expires_in) ||
      response.expires_in < 1 ||
      response.expires_in > 3600
    )
      throw new HttpError('Resposta de login inválida.');
    this.token = response.access_token;
    this.expiresAt = Date.now() + response.expires_in * 1000;
  }

  listLogs(query: LogQuery): Promise<LogPage> {
    const search = queryString(query);
    return this.request<LogPage>(`/logs${search ? `?${search}` : ''}`);
  }

  getLog(id: string): Promise<LogRead> {
    return this.request<LogRead>(`/logs/${id}`);
  }
  listApplications(): Promise<ApplicationList> {
    return this.request<ApplicationList>('/applications');
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    authorized = true,
  ): Promise<T> {
    if (authorized && !this.hasSession())
      throw new HttpError('Sessão encerrada. Faça login novamente.', 401);
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    if (authorized && this.token)
      headers.set('Authorization', `Bearer ${this.token}`);
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers,
        cache: 'no-store',
        signal: AbortSignal.timeout(15000),
      });
    } catch {
      throw new HttpError('Não foi possível conectar à API local.');
    }
    if (response.status === 401 && authorized) this.logout();
    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        /* HTTP sem corpo JSON */
      }
      const title =
        typeof detail === 'object' &&
        detail !== null &&
        'title' in detail &&
        typeof detail.title === 'string'
          ? detail.title
          : undefined;
      throw new HttpError(
        title ?? `Erro HTTP ${response.status}.`,
        response.status,
      );
    }
    try {
      return (await response.json()) as T;
    } catch {
      throw new HttpError('Resposta inválida da API.');
    }
  }
}
