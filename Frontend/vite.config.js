import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Expose environment variables to the frontend
  // Access via import.meta.env.VITE_API_URL
  define: {
    'process.env': {}
  }
})
