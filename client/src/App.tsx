import { useState } from 'react'
import EditorPanel from './components/editor-panel/editor-layout' // Update path if needed
import ResumeViewer from './components/editor-panel//ResumeViewer' // Update path if needed
import './App.css' // Make sure your CSS file is imported

function App() {
  // The central brain holding the compiled JSON from the left panel
  const [masterResumeData, setMasterResumeData] = useState<
    Record<string, unknown[]>
  >({})

  return (
    // The main flexbox container
    <div className="editor-page">
      {/* LEFT HALF: The Editor */}
      <div className="editor-pane">
        <EditorPanel
          onDataChange={(compiledData) => setMasterResumeData(compiledData)}
        />
      </div>

      {/* RIGHT HALF: The PDF Viewer */}
      <div className="viewer-pane">
        <ResumeViewer aggregatedData={masterResumeData} />
      </div>
    </div>
  )
}

export default App
