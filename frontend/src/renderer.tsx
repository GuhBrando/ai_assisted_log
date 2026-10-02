import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Login } from './renderer/Login';
import { Logs } from './renderer/Logs';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function App(): React.JSX.Element {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  useEffect(() => {
    void window.logApi
      .session()
      .then((result) => setAuthenticated(result.ok && result.data));
  }, []);
  async function login(
    email: string,
    password: string,
  ): Promise<string | null> {
    const result = await window.logApi.login({ email, password });
    if (!result.ok) return result.error.message;
    queryClient.clear();
    setAuthenticated(true);
    return null;
  }
  function logout(): void {
    void window.logApi.logout();
    queryClient.clear();
    setAuthenticated(false);
  }
  if (authenticated === null)
    return <main className="boot-state">Abrindo Log Insight…</main>;
  return authenticated ? (
    <Logs onLogout={logout} onExpired={logout} />
  ) : (
    <Login onLogin={login} />
  );
}

const root = document.getElementById('root');
if (!root) throw new Error('Elemento raiz não encontrado.');
createRoot(root).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
);
