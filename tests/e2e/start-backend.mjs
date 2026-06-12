import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';

const repoRoot = process.cwd();
const port = process.argv[2] || process.env.PORT || '5011';

const candidates = [
  join(repoRoot, 'backend', '.venv', 'Scripts', 'python.exe'),
  join(repoRoot, 'backend', '.venv', 'bin', 'python'),
  'python',
  'python3'
];

const python = candidates.find((candidate) => candidate.includes('\\') || candidate.includes('/') ? existsSync(candidate) : true);

if (!python) {
  console.error('No Python executable found for e2e backend startup.');
  process.exit(1);
}

const child = spawn(
  python,
  [join(repoRoot, 'tests', 'e2e', 'run_backend_no_reloader.py'), port],
  {
    cwd: repoRoot,
    env: {
      ...process.env,
      PORT: port
    },
    stdio: 'inherit'
  }
);

function stop() {
  if (!child.killed) {
    child.kill();
  }
}

process.on('SIGTERM', () => {
  stop();
  process.exit(0);
});
process.on('SIGINT', () => {
  stop();
  process.exit(0);
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.exit(0);
  }
  process.exit(code ?? 0);
});
