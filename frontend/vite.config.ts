import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const backend = env.BACKEND_URL || 'http://127.0.0.1:8000'
  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      // датасет лежит на уровень выше (../case_1), разрешаем читать его
      fs: { allow: ['..'] },
      proxy: {
        '/api': backend,
        '/health': backend,
      },
    },
    preview: {
      host: true,
      proxy: { '/api': backend, '/health': backend },
    },
  }
})
