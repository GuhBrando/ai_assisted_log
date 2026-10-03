import React, { useState } from 'react';
import { useApiTargetLabel } from './api-target';

interface Props {
  onLogin: (email: string, password: string) => Promise<string | null>;
}

export function Login({ onLogin }: Props): React.JSX.Element {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const apiLabel = useApiTargetLabel();
  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      setError((await onLogin(email, password)) ?? '');
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-brand">
        <span className="brand-symbol">⌁</span>
        <span>LOG INSIGHT</span>
      </div>
      <form className="login-card" onSubmit={(event) => void submit(event)}>
        <span className="eyebrow">OBSERVABILIDADE / DESKTOP</span>
        <h1>Entre para investigar.</h1>
        <p className="muted">
          Acesse os logs do seu cliente com sua conta da plataforma.
        </p>
        <label>
          E-mail
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="voce@empresa.com"
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? 'Conectando…' : 'Entrar'}
        </button>
        <p className="login-footnote">{apiLabel}</p>
      </form>
    </main>
  );
}
