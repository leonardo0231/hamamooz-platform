import { defineConfig } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)));
const sourceRoot = resolve(projectRoot, 'src');

export default defineConfig({
  root: sourceRoot,
  publicDir: resolve(projectRoot, 'public'),
  base: '/',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
  },
  build: {
    outDir: resolve(projectRoot, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: resolve(sourceRoot, 'index.html'),
        reportSample: resolve(sourceRoot, 'report-sample.html'),
      },
    },
  },
});
