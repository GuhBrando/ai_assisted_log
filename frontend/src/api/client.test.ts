import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, HttpError } from './client';

afterEach(() => vi.unstubAllGlobals());

describe('cliente HTTP do processo principal', () => {
  it('mantém o bearer só no processo principal e encerra a sessão em 401', async () => {
    const calls: Array<{ url: string; authorization: string | null }> = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init: RequestInit) => {
        calls.push({
          url,
          authorization: new Headers(init.headers).get('Authorization'),
        });
        if (url.endsWith('/auth/login'))
          return new Response(
            JSON.stringify({
              access_token: 'secret-token',
              token_type: 'bearer',
              expires_in: 3600,
            }),
            { status: 200 },
          );
        return new Response(JSON.stringify({ title: 'Unauthorized' }), {
          status: 401,
        });
      }),
    );
    const client = new ApiClient('http://127.0.0.1:4010');
    await client.login({ email: 'ana@example.com', password: 'long-password' });
    expect(client.hasSession()).toBe(true);
    await expect(client.listLogs({ limit: 50 })).rejects.toMatchObject({
      status: 401,
    });
    expect(calls[0].authorization).toBeNull();
    expect(calls[1].authorization).toBe('Bearer secret-token');
    expect(client.hasSession()).toBe(false);
    await expect(client.listApplications()).rejects.toBeInstanceOf(HttpError);
    expect(calls).toHaveLength(2);
  });

  it('mostra o detail do Problem Details e usa o title só como alternativa', async () => {
    const problems = [
      { title: 'Unauthorized', status: 401, detail: 'Credenciais inválidas' },
      { title: 'Unauthorized', status: 401 },
    ];
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify(problems.shift()), { status: 401 }),
      ),
    );
    const client = new ApiClient('http://127.0.0.1:8000');
    const credentials = { email: 'ana@example.com', password: 'errada' };
    await expect(client.login(credentials)).rejects.toMatchObject({
      message: 'Credenciais inválidas',
      status: 401,
    });
    await expect(client.login(credentials)).rejects.toMatchObject({
      message: 'Unauthorized',
    });
  });
});
