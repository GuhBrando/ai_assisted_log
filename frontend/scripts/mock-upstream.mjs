import http from 'node:http';
import { applications, createMockLogs, listMockLogs } from './mock-data.mjs';

const logs = createMockLogs();
const byId = new Map(logs.map((log) => [log.id, log]));
const token =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtb2NrLXVzZXIifQ.mock';

function send(response, status, data) {
  response.writeHead(status, {
    'Content-Type':
      status >= 400 ? 'application/problem+json' : 'application/json',
    'Cache-Control': 'no-store',
  });
  response.end(JSON.stringify(data));
}

export function createMockUpstream() {
  return http.createServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://127.0.0.1:4011');
    if (request.method === 'POST' && url.pathname === '/auth/login') {
      for await (const _part of request) {
        /* consume body without retaining credentials */
      }
      send(response, 200, {
        access_token: token,
        token_type: 'bearer',
        expires_in: 3600,
      });
      return;
    }
    if (request.method === 'GET' && url.pathname === '/applications') {
      send(response, 200, { items: applications });
      return;
    }
    if (request.method === 'GET' && url.pathname === '/logs') {
      send(response, 200, listMockLogs(logs, url.searchParams));
      return;
    }
    if (
      request.method === 'GET' &&
      /^\/logs\/[a-f\d]{24}$/i.test(url.pathname)
    ) {
      const log = byId.get(url.pathname.slice(6));
      if (log) send(response, 200, log);
      else
        send(response, 404, {
          type: 'about:blank',
          title: 'Not Found',
          status: 404,
          detail: 'Log não encontrado.',
        });
      return;
    }
    send(response, 404, {
      type: 'about:blank',
      title: 'Not Found',
      status: 404,
      detail: 'Recurso não encontrado.',
    });
  });
}
