import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const backend = env.BACKEND_URL || 'http://127.0.0.1:8000'
  const proxy = { '/api': backend, '/health': backend, '/docs': backend, '/redoc': backend, '/openapi.json': backend }
  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      // Employee data comes through the authenticated API. Keep backend files private.
      fs: {
        strict: true,
        allow: ['.'],
        deny: ['.env', '.env.*', '*.{crt,pem}', '**/.git/**', '**/.local/**', '**/*.db', '**/*.sqlite', '**/*.sqlite3'],
      },
      proxy,
    },
    preview: {
      host: true,
      proxy,
    },
  }
})
