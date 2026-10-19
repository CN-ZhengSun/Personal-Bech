import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      // 前端 /api 请求代理到后端 FastAPI
      '/api/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // 附件静态资源转发到后端
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})
