import { defineConfig } from 'file:///E:/5703/learning-assistant/frontend/node_modules/vite/dist/node/index.js';
export default defineConfig({
  root: 'E:/5703/learning-assistant/frontend',
  envDir: false,
  cacheDir: 'C:/Users/PC/Documents/Codex/2026-10-04/task-2/5703-dev89-runtime/vite-cache',
  server: {
    host: '127.0.0.1', port: 15198, strictPort: true,
    watch: { ignored: ['**/.browser-profiles/**'] },
    proxy: { '/api': { target: 'http://127.0.0.1:18029', changeOrigin: true } },
  },
});
