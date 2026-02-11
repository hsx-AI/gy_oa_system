import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',  // 允许通过IP地址访问
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // FastAPI 后端地址
        changeOrigin: true,
        secure: false
      }
    }
  }
})
