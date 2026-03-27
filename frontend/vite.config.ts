import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0', // 允许远程访问
    port: 3000,
    strictPort: true,
    allowedHosts: [
      '1203862ikgl90.vicp.fun',
      '.vicp.fun',
      '.vicp.io',
      'localhost',
      '10.40.10.229',
      '183.6.114.147',
    ], // 允许的外网域名
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
