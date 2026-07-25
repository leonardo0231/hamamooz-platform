import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
const directory = resolve(process.argv[2] || 'dist');
const port = Number(process.argv[3] || 4173);
const mime = { '.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.map':'application/json; charset=utf-8','.svg':'image/svg+xml' };
createServer(async (request, response) => {
  try {
    const url = new URL(request.url || '/', 'http://localhost');
    let target = resolve(directory, `.${decodeURIComponent(url.pathname)}`);
    if (!target.startsWith(directory)) throw new Error('invalid path');
    try { if ((await stat(target)).isDirectory()) target = resolve(target, 'index.html'); }
    catch { target = resolve(directory, 'index.html'); }
    const body = await readFile(target);
    response.writeHead(200, { 'Content-Type': mime[extname(target)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    response.end(body);
  } catch {
    response.writeHead(404); response.end('Not found');
  }
}).listen(port, '127.0.0.1', () =>
  console.log(`"HamAmoz frontend: http://127.0.0.1:${port}"`)
);