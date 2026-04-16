import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/agent': {
          target: env.VITE_API_BASE_URL,
          changeOrigin: true,
        },
        '/knowledgebase': {
          target: env.VITE_API_BASE_URL,
          changeOrigin: true,
        },
      },
    },
  }
})
