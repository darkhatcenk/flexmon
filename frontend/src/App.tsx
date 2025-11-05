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
  const { isAuthenticated, isBootstrapping, user } = useAuthStore()

  useEffect(() => {
    // Bootstrap auth on mount
    authStore.bootstrap()
  }, [])

  // Show loading spinner while bootstrapping
  if (isBootstrapping) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '18px',
        color: '#6b7280'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: '16px', fontSize: '24px' }}>⚙️</div>
          <div>Loading FlexMON...</div>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />

      <Route path="/*" element={
        isAuthenticated ? (
          <div className="app">
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
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/servers" element={<Servers />} />
                  <Route path="/servers/:hostname" element={<ServerDetail />} />
                  <Route path="/logs" element={<Logs />} />
                  <Route path="/alarms" element={<Alarms />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/discover" element={<Discover />} />
                  <Route path="/users" element={
                    <ProtectedRoute requiredRoles={['platform_admin', 'tenant_admin']}>
                      <Users />
                    </ProtectedRoute>
                  } />
                  <Route path="/platform-logs" element={<PlatformLogs />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </main>
            </div>
          </div>
        ) : (
          <Navigate to="/login" replace />
        )
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
