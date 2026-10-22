import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The Python package serves the UI from src/specdiff/ui_dist (see api.py).
  build: { outDir: '../src/specdiff/ui_dist', emptyOutDir: true },
  // In `npm run dev`, proxy API calls to a running `specdiff ui --no-browser`.
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
