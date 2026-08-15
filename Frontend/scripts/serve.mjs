import { createReadStream } from 'node:fs';
import { access, stat } from 'node:fs/promises';
import { createServer, request as proxyRequest } from 'node:http';
import { extname, resolve, sep } from 'node:path';

const directory = resolve(process.argv[2] ?? 'src');
const port = Number(process.argv[3] ?? 5173);
const publicDirectory = resolve('public');
const types = {
  '.css': 'text/css; charset=utf-8', '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
};

async function existingFile(pathname) {
  const clean = decodeURIComponent(pathname.split('?')[0]).replace(/^\/+/, '');
  for (const base of [directory, publicDirectory]) {
    const candidate = resolve(base, clean || 'index.html');
    if (!candidate.startsWith(`${base}${sep}`) && candidate !== base) continue;
    try { if ((await stat(candidate)).isFile()) return candidate; } catch {}
  }
  const fallback = resolve(directory, 'index.html');
  await access(fallback);
  return fallback;
}

createServer(async (request, response) => {
  if ((request.url ?? '').startsWith('/api/')) {
    const target = new URL(request.url, 'http://127.0.0.1:8000');
    const upstream = proxyRequest(target, { method: request.method, headers: { ...request.headers, host: '127.0.0.1:8000' } }, proxy => {
      response.writeHead(proxy.statusCode ?? 502, proxy.headers);
      proxy.pipe(response);
    });
    upstream.on('error', () => {
      response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      response.end(JSON.stringify({ error: { code: 'dev_proxy_unavailable', detail: 'Backend is not available on port 8000.' } }));
    });
    request.pipe(upstream);
    return;
  }
  try {
    const file = await existingFile(request.url ?? '/');
    response.writeHead(200, {
      'Content-Type': types[extname(file)] ?? 'application/octet-stream',
      'Cache-Control': file.endsWith('index.html') ? 'no-store' : 'public, max-age=300',
      'X-Content-Type-Options': 'nosniff',
    });
    createReadStream(file).pipe(response);
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not found');
  }
}).listen(port, '0.0.0.0', () => console.log(`HamAmoz UI: http://localhost:${port}`));
