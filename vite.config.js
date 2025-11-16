import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/cio-react/',   // repo adı neyse o
  base: '/cio-react-game-clean/', // Örn: /cio-react-game-clean/
  plugins: [react()],
})