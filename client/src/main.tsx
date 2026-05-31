import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

// 1. Import your new AuthProvider
import { AuthProvider } from './auth/AuthProvider'

// (Keep your global CSS imports here, e.g., import './index.css')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* 2. Wrap the entire app so useAuth works globally */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
)
