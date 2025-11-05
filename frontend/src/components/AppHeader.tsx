import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore, authStore } from '../lib/auth'

export default function AppHeader() {
  const { user } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!user) return null

  // Get user initials for avatar
  const initials = user.username
    .split(/[\s_-]/)
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)

  const roleLabel = {
    platform_admin: 'Platform Admin',
    tenant_admin: 'Admin',
    tenant_reporter: 'Reporter'
  }[user.role] || user.role

  return (
    <header style={{
      height: '64px',
      backgroundColor: 'white',
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
    }}>
      <div style={{
        fontSize: '20px',
        fontWeight: '700',
        color: '#667eea',
        letterSpacing: '-0.5px'
      }}>
        FlexMON
      </div>

      <div style={{ position: 'relative' }} ref={menuRef}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '8px 12px',
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#f3f4f6'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#f9fafb'
          }}
        >
          {/* User avatar */}
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: '#667eea',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: '600'
          }}>
            {initials}
          </div>

          {/* User info */}
          <div style={{ textAlign: 'left', lineHeight: '1.4' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#1f2937'
            }}>
              {user.username}
            </div>
            <div style={{
              fontSize: '12px',
              color: '#6b7280'
            }}>
              {roleLabel}
            </div>
          </div>

          {/* Dropdown arrow */}
          <div style={{
            fontSize: '12px',
            color: '#9ca3af',
            transition: 'transform 0.2s',
            transform: menuOpen ? 'rotate(180deg)' : 'rotate(0deg)'
          }}>
            ▼
          </div>
        </button>

        {/* Dropdown menu */}
        {menuOpen && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            minWidth: '200px',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            overflow: 'hidden',
            zIndex: 1000
          }}>
            <Link
              to="/settings"
              onClick={() => setMenuOpen(false)}
              style={{
                display: 'block',
                padding: '12px 16px',
                fontSize: '14px',
                color: '#374151',
                textDecoration: 'none',
                transition: 'background-color 0.2s',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f9fafb'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'white'
              }}
            >
              ⚙️ Settings
            </Link>

            <div
              onClick={() => {
                setMenuOpen(false)
                authStore.logout()
              }}
              style={{
                display: 'block',
                padding: '12px 16px',
                fontSize: '14px',
                color: '#dc2626',
                borderTop: '1px solid #f3f4f6',
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#fef2f2'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'white'
              }}
            >
              🚪 Logout
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
