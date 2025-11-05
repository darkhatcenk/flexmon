import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../lib/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRoles?: string[]
}

export default function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  // If not authenticated, redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // If specific roles are required, check them
  if (requiredRoles && requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.includes(user.role)

    if (!hasRequiredRole) {
      // Show 403 Forbidden page
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '72px', marginBottom: '24px' }}>🔒</div>
          <h1 style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#dc2626',
            marginBottom: '16px'
          }}>
            Access Denied
          </h1>
          <p style={{
            fontSize: '16px',
            color: '#6b7280',
            marginBottom: '32px',
            maxWidth: '500px'
          }}>
            You don't have the required permissions to access this page.
            {requiredRoles && requiredRoles.length > 0 && (
              <span style={{ display: 'block', marginTop: '8px', fontSize: '14px' }}>
                Required role: {requiredRoles.join(', ')}
              </span>
            )}
          </p>
          <button
            onClick={() => window.history.back()}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: '600',
              color: 'white',
              backgroundColor: '#667eea',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            Go Back
          </button>
        </div>
      )
    }
  }

  return <>{children}</>
}
