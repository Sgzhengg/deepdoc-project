import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { mobileEntryPlugin } from './vite-plugin-mobile-entry'

export default defineConfig({
  plugins: [
    react(),
    mobileEntryPlugin(), // 移动端入口插件
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3001,
    strictPort: true,
    allowedHosts: [
      '.vicp.fun',
      '.vicp.io',
      'localhost',
      '10.40.10.229',
      '183.6.114.147',
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['react-syntax-highlighter'],
    include: ['react', 'react-dom'],
  },
})
