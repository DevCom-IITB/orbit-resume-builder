import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import './App.css'
import { useAuth } from './auth/AuthProvider'

type VerifyResponse = {
  user?: string
  id?: number | string
  role?: string
  profile?: {
    username?: string
    email?: string
    first_name?: string
    last_name?: string
  }
  error?: string
}

function App() {
  const { token, setToken } = useAuth()
  const [status, setStatus] = useState('Waiting for token from REACH...')
  const [verifyData, setVerifyData] = useState<VerifyResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const verifyUrl = import.meta.env.VITE_REACH_VERIFY_URL || 'http://127.0.0.1:8000/api/sso/accounts/verify/'
  const serviceKey = import.meta.env.VITE_RB_SERVICE_KEY || 'dev-resume-key-1'

  const authSummary = useMemo(() => {
    if (!token) return 'No token in React state'
    return `Token loaded in React state (${token.slice(0, 12)}...)`
  }, [token])

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (!event.data || typeof event.data !== 'object') return
      if (event.data.type === 'REACH_TOKEN') {
        setToken(event.data.token ?? null)
        setStatus('Token received from REACH parent')
      }
      if (event.data.type === 'RB_READY') {
        setStatus('RB iframe ready')
      }
    }

    window.addEventListener('message', onMessage)
    window.parent.postMessage({ type: 'REQUEST_TOKEN' }, '*')

    return () => window.removeEventListener('message', onMessage)
  }, [setToken])

  const requestToken = () => {
    window.parent.postMessage({ type: 'REQUEST_TOKEN' }, '*')
    setStatus('Requested token from REACH parent')
  }

  const verifyToken = async () => {
    if (!token) {
      setStatus('No token available to verify')
      return
    }

    setLoading(true)
    setStatus('Verifying token against REACH...')

    try {
      const response = await axios.get<VerifyResponse>(verifyUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Service-Key': serviceKey,
        },
      })
      setVerifyData(response.data)
      setStatus('Token verified successfully')
    } catch (error: any) {
      const message = error?.response?.data?.error || error?.message || 'Verification failed'
      setVerifyData({ error: message })
      setStatus(message)
      if (error?.response?.status === 401) {
        window.parent.postMessage({ type: 'REQUEST_TOKEN' }, '*')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="card">
        <p className="eyebrow">Resume Builder / Auth Test</p>
        <h1>RB iframe handshake</h1>
        <p className="muted">{status}</p>
        <p>{authSummary}</p>

        <div className="actions">
          <button type="button" onClick={requestToken}>Request token</button>
          <button type="button" onClick={verifyToken} disabled={!token || loading}>
            {loading ? 'Verifying…' : 'Verify on REACH'}
          </button>
          <button type="button" onClick={() => setToken(null)}>Clear state</button>
        </div>

        <div className="panel">
          <strong>Verify endpoint</strong>
          <code>{verifyUrl}</code>
        </div>

        <div className="panel">
          <strong>Token in React state only</strong>
          <code>{token ? `${token.slice(0, 24)}…` : 'none'}</code>
        </div>

        <pre className="response">{verifyData ? JSON.stringify(verifyData, null, 2) : 'No verify response yet'}</pre>
      </div>
    </div>
  )
}

export default App
