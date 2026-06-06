import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'

import { APIInstance } from '../lib/api'

type AuthContextType = {
  token: string | null
  setToken: (t: string | null) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  

  const [token, setToken] = useState<string | null>(null)
  const pendingRefresh = useRef<((t: string | null) => void) | null>(null)
  

  useEffect(() => {
    // Update axios default header when token changes
    if (token) {
      APIInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete APIInstance.defaults.headers.common['Authorization']
    }
  }, [token])

  useEffect(() => {
    const onMessage = (ev: MessageEvent) => {
      // Expect messages from parent with shape { type: 'REACH_TOKEN', token: '...' }
      if (!ev.data || typeof ev.data !== 'object') return
      if (ev.data.type === 'REACH_TOKEN') {
        const t = ev.data.token || null
        setToken(t)
        // Resolve any pending refresh waiter
        if (pendingRefresh.current) {
          pendingRefresh.current(t)
          pendingRefresh.current = null
        }
      }
      // Parent can also request handshake
      if (ev.data.type === 'REQUEST_TOKEN_ACK') {
        // reply to let parent know we are ready
        window.parent.postMessage({ type: 'RB_READY' }, '*')
      }
    }

    window.addEventListener('message', onMessage)
    // Notify parent we are ready to receive token
    window.parent.postMessage({ type: 'RB_READY' }, '*')

    return () => window.removeEventListener('message', onMessage)
  }, [])

  // Called when axios receives 401: ask parent for fresh token and wait
  const requestTokenFromParent = (): Promise<string | null> =>
    new Promise((resolve) => {
      pendingRefresh.current = resolve
      window.parent.postMessage({ type: 'REQUEST_TOKEN' }, '*')
      // fallback timeout
      setTimeout(() => {
        if (pendingRefresh.current) {
          pendingRefresh.current = null
          resolve(null)
        }
      }, 10000)
    })

  // Axios response interceptor to handle 401
  useEffect(() => {
    const id = APIInstance.interceptors.response.use(
      (res) => res,
      async (error) => {
        const original = error.config
        if (
          error.response &&
          error.response.status === 401 &&
          !original._retry
        ) {
          original._retry = true
          const newToken = await requestTokenFromParent()
          if (newToken) {
            setToken(newToken)
            original.headers['Authorization'] = `Bearer ${newToken}`
            return APIInstance(original)
          }
        }
        return Promise.reject(error)
      }
    )

    return () => APIInstance.interceptors.response.eject(id)
  }, [])

  return (
    <AuthContext.Provider value={{ token, setToken }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export default AuthProvider
