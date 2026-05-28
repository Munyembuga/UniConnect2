import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // /api/auth/login  →  http://localhost:8000/api/v1/auth/login
        rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
      },
    },
  },
})
