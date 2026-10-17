import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.')
  return {
    plugins: [react()],
    // 화면이 /api/... 로 보내는 요청을 주소 그대로 실제 서버로 넘긴다 (VITE_API_MODE가 mixed, real 일 때 쓰임)
    server: {
      // 다른 곳에서 시연할 때 Cloudflare 임시 터널 주소(*.trycloudflare.com)로 들어오는 접속을 허용한다
      allowedHosts: ['.trycloudflare.com'],
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
