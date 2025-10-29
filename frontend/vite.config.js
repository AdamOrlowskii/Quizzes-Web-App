import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [vue(), vueDevTools()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:7000',
        changeOrigin: true,
        secure: false,
        rewrite: path => path.replace(/^\/api/, ''), // ← DODAJ TO!
      },
      '^/(login|users|quizzes|auth|register|logout|favourites|questions)': {
        target: 'http://backend:7000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src/', import.meta.url)),
    },
  },
})
