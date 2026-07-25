import { watch } from 'node:fs';
import { access } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const buildScript = resolve(root, 'scripts/build.mjs');

function build() {
  const result = spawnSync(process.execPath, [buildScript], { cwd: root, stdio: 'inherit' });
  return !result.error && result.status === 0;
}

if (!build()) process.exit(1);
const server = spawn(process.execPath, [resolve(root, 'scripts/serve.mjs'), 'dist', '5173'], { cwd: root, stdio: 'inherit' });
let timer;
let building = false;
let queued = false;

function scheduleBuild() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (building) { queued = true; return; }
    building = true;
    build();
    building = false;
    if (queued) { queued = false; scheduleBuild(); }
  }, 120);
}

const watchers = [watch(resolve(root, 'src'), { recursive: true }, scheduleBuild)];
try {
  await access(resolve(root, '.env'));
  watchers.push(watch(resolve(root, '.env'), scheduleBuild));
} catch {}

function shutdown(signal) {
  watchers.forEach(item => item.close());
  server.kill(signal);
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
server.on('exit', code => process.exit(code ?? 0));
