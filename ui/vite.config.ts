import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Allow serving under FastAPI at /web/ in production builds
  // Set VITE_BASE=/web/ for prod (demo script does this)
  base: process.env.VITE_BASE || '/',
  server: {
    port: 5173,
    strictPort: true
  },
  build: {
    outDir: 'dist'
  }
})
