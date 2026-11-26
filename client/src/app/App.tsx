import { useEffect } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import EditorApp from '../App'
import { isFromReach } from '../auth/reachMessaging'
import Home from './pages/Home'

function App() {
    const navigate = useNavigate()

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            if (!isFromReach(event)) return
            if (event.data && event.data.type === 'NAVIGATE_HOME') {
                navigate('/home')
            }
        }
        window.addEventListener('message', handleMessage)
        return () => window.removeEventListener('message', handleMessage)
    }, [navigate])

    return (
        <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/home" element={<Home />} />
            <Route path="/editor/:resumeId" element={<EditorApp />} />
            <Route path="/editor" element={<EditorApp />} />
        </Routes>
    )
}

export default App
