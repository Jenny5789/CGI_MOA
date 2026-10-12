import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.')
  return {
    plugins: [react()],
    // 화면이 /api/... 로 보내는 요청을 주소 그대로 실제 서버로 넘긴다 (VITE_USE_MOCK=false 일 때만 쓰임)
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
