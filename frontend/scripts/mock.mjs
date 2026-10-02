import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { createMockUpstream } from './mock-upstream.mjs';

const require = createRequire(import.meta.url);
const prism = require.resolve('@stoplight/prism-cli/dist/index.js');
const upstream = createMockUpstream();
upstream.listen(4011, '127.0.0.1', () => {
  console.log('Massa de 1.600 logs disponível ao Prism no loopback interno.');
  const child = spawn(
    process.execPath,
    [
      prism,
      'proxy',
      '../docs/api/openapi.yaml',
      'http://127.0.0.1:4011',
      '-h',
      '127.0.0.1',
      '-p',
      '4010',
    ],
    { cwd: new URL('..', import.meta.url), stdio: 'inherit' },
  );
  child.on('exit', (code) => {
    upstream.close();
    process.exitCode = code ?? 0;
  });
  for (const signal of ['SIGINT', 'SIGTERM'])
    process.on(signal, () => {
      child.kill(signal);
      upstream.close();
    });
});
