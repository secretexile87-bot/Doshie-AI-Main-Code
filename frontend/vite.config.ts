import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://127.0.0.1:5000',
      '/health': 'http://127.0.0.1:5000',
      '/dashboard': 'http://127.0.0.1:5000',
      '/profiles': 'http://127.0.0.1:5000',
      '/chat-history': 'http://127.0.0.1:5000',
      '/new-chat': 'http://127.0.0.1:5000',
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
