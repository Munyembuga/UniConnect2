import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Home           from './pages/Home'
import Chat           from './pages/Chat'
import Login          from './pages/Login'
import AdminDashboard from './pages/AdminDashboard'
import { getToken, isAdmin } from './services/api'

function RequireAdmin({ children }) {
  if (!getToken() || !isAdmin()) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"      element={<Home />} />
        <Route path="/chat"  element={<Chat />} />
        <Route path="/login" element={<Login />} />
        <Route path="/admin" element={<RequireAdmin><AdminDashboard /></RequireAdmin>} />
        <Route path="*"      element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
