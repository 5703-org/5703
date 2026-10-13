export default {
  root: 'E:/5703/learning-assistant/frontend',
  cacheDir: 'C:/Users/PC/Documents/Codex/2026-10-04/task-2/5703-proof60-browser/vite-cache',
  server: {
    host: '127.0.0.1', port: 15199, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:18029', changeOrigin: true } },
  },
};
