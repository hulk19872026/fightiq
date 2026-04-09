import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/events': 'http://localhost:8000',
      '/fighter-stats': 'http://localhost:8000',
      '/fight-analysis': 'http://localhost:8000',
      '/odds': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
    }
  }
})
