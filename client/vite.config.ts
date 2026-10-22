import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '')
    const reachOrigin = env.VITE_REACH_ORIGIN || 'http://localhost:3000'

    return {
        plugins: [react()],
        server: {
            port: 5173,
            strictPort: true,
            headers: {
                // Only REACH may embed Orbit. ("X-Frame-Options: ALLOWALL" is
                // not a real value, so browsers let any site frame the app.)
                'Content-Security-Policy': `frame-ancestors 'self' ${reachOrigin}`,
            },
        },
    }
})
