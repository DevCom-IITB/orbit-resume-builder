import { useState } from 'react'
import { useAuth } from './auth/AuthProvider' // Adjust this import path as needed
import EditorPanel from './components/editor-panel/editor-layout' // Adjust this import path as needed
import ResumeViewer from './components/editor-panel/ResumeViewer' // Adjust this import path as needed

function App() {
  // 1. Grab the token from AuthContext
  const { token } = useAuth()

  // 2. Your state for the split-screen layout and data
  const [isViewerExpanded, setIsViewerExpanded] = useState(false)
  const [masterResumeData, setMasterResumeData] = useState<Record<string, unknown>>({})

  // 3. The Auth Gate
  // If the iframe hasn't received the token from REACH yet, show a loading screen.
  if (!token) {
    return (
      <div className="app-shell">
        <div className="card" style={{ textAlign: 'center', marginTop: '20vh' }}>
          <h2>Authenticating...</h2>
          <p className="muted">
            Waiting for secure token from REACH.
          </p>
        </div>
      </div>
    )
  }

  // 4. Once the token exists, render your actual app!
  return (
    <div 
      className="editor-page" 
      style={{ 
        display: 'flex', 
        gap: '16px', 
        height: '100vh', 
        overflow: 'hidden' 
      }}
    >
      {/* Conditionally hide the editor if the viewer is expanded */}
      {!isViewerExpanded && (
        <div className="editor-pane">
          <EditorPanel
            onDataChange={(compiledData) => setMasterResumeData(compiledData)}
          />
        </div>
      )}

      {/* Viewer pane flexes to take up remaining space */}
      <div className="viewer-pane" style={{ flex: 1 }}>
        <ResumeViewer
          aggregatedData={masterResumeData}
          isExpanded={isViewerExpanded}
          onToggleExpand={() => setIsViewerExpanded(!isViewerExpanded)}
        />
      </div>
    </div>
  )
}

export default App