import { defineConfig } from 'vitest/config';

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
    watch: { ignored: ['**/.browser-profiles/**'] },
    proxy: { '/api': { target: process.env.API_PROXY_URL || 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  preview: { port: 4173, strictPort: true },
  test: { environment: 'jsdom', include: ['src/**/*.test.{ts,tsx}'], restoreMocks: true },
});
