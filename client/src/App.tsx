import { useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import EditorPanel from './components/editor-panel/editor-layout'
import ResumeViewer from './components/editor-panel/ResumeViewer'
import './App.css'

function App() {
    // 1. Grab the token from  AuthContext
    const { token } = useAuth()

    // Your state for the split-screen layout
    const [masterResumeData, setMasterResumeData] = useState<
        Record<string, unknown>
    >({})

    // 2. The Auth Gate
    // If the iframe hasn't received the token from REACH yet, show a loading screen.
    // This prevents your app from crashing or making unauthorized API calls.
    if (!token) {
        return (
            <div className="app-shell">
                <div className="card" style={{ textAlign: 'center' }}>
                    <h2>Authenticating...</h2>
                    <p className="muted">
                        Waiting for secure token from REACH.
                    </p>
                </div>
            </div>
        )
    }

    // 3. Once the token exists, render your actual app!
    return (
        <div className="editor-page">
            <div className="editor-pane">
                <EditorPanel
                    onDataChange={(compiledData) =>
                        setMasterResumeData(compiledData)
                    }
                />
            </div>

            <div className="viewer-pane">
                <ResumeViewer aggregatedData={masterResumeData} />
            </div>
        </div>
    )
}

export default App
