import { Navigate, Route, Routes } from 'react-router-dom'
import EditorApp from '../App'
import Home from './pages/Home'

function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/home" element={<Home />} />
            <Route path="/editor" element={<EditorApp />} />
        </Routes>
    )
}

export default App
