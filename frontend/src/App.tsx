import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Servers from './pages/Servers'
import ServerDetail from './pages/ServerDetail'
import Logs from './pages/Logs'
import Alarms from './pages/Alarms'
import Users from './pages/Users'
import Settings from './pages/Settings'
import Reports from './pages/Reports'
import Discover from './pages/Discover'
import PlatformLogs from './pages/PlatformLogs'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'
import AppHeader from './components/AppHeader'
import { authStore, useAuthStore } from './lib/auth'

function AppContent() {
  const { isAuthenticated, user } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // On mount, try to fetch current user if token exists
    const initAuth = async () => {
      if (authStore.getState().token) {
        await authStore.fetchCurrentUser()
      }
      setLoading(false)
    }
    initAuth()
  }, [])

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '18px',
        color: '#6b7280'
      }}>
        Loading...
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />

      <Route path="/*" element={
        <div className="app">
          {isAuthenticated && (
            <>
              <AppHeader />
              <div style={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
                <nav className="sidebar">
                  <ul>
                    <li><Link to="/">Dashboard</Link></li>
                    <li><Link to="/servers">Servers</Link></li>
                    <li><Link to="/logs">Logs</Link></li>
                    <li><Link to="/alarms">Alarms</Link></li>
                    <li><Link to="/reports">Reports</Link></li>
                    <li><Link to="/discover">Discover</Link></li>
                    {user && ['platform_admin', 'tenant_admin'].includes(user.role) && (
                      <li><Link to="/users">Users</Link></li>
                    )}
                    <li><Link to="/platform-logs">Platform Logs</Link></li>
                    <li><Link to="/settings">Settings</Link></li>
                  </ul>
                </nav>
                <main className="content">
                  <Routes>
                    <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                    <Route path="/servers" element={<ProtectedRoute><Servers /></ProtectedRoute>} />
                    <Route path="/servers/:hostname" element={<ProtectedRoute><ServerDetail /></ProtectedRoute>} />
                    <Route path="/logs" element={<ProtectedRoute><Logs /></ProtectedRoute>} />
                    <Route path="/alarms" element={<ProtectedRoute><Alarms /></ProtectedRoute>} />
                    <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
                    <Route path="/discover" element={<ProtectedRoute><Discover /></ProtectedRoute>} />
                    <Route path="/users" element={
                      <ProtectedRoute requiredRoles={['platform_admin', 'tenant_admin']}>
                        <Users />
                      </ProtectedRoute>
                    } />
                    <Route path="/platform-logs" element={<ProtectedRoute><PlatformLogs /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                  </Routes>
                </main>
              </div>
            </>
          )}
        </div>
      } />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
