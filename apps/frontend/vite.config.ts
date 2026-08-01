import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        ...(process.env.NODE_ENV !== 'production'
          ? { 'b3-1-fixture': resolve(__dirname, 'src/e2e/fixtures/b3-1-button-fixture.html') }
          : {}),
      },
      output: {
        manualChunks(id) {
          if (id.includes('/vis-network/')) return 'vis-network';
          if (id.includes('/vis-data/')) return 'vis-data';
          if (id.includes('/vis-util/')) return 'vis-util';
        },
      },
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ready': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
