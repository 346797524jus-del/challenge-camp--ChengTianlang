import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    emptyOutDir: false
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true
        // 注意：后端有 context-path: /api，所以不需要 rewrite
        // 前端请求 /api/agent/chat -> 代理到 http://localhost:8081/api/agent/chat
      }
    }
  }
})
